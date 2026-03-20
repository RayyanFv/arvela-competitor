'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase/client'
import {
    Users, TrendingUp, Target,
    Building2, Activity, Clock
} from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Breadcrumbs } from '@/components/layout/Breadcrumbs'
import {
    ChartContainer,
    ChartTooltip,
    ChartTooltipContent,
} from '@/components/ui/chart'
import {
    BarChart, Bar, XAxis, YAxis, ResponsiveContainer,
    Cell, PieChart, Pie, Tooltip as RechartsTooltip
} from 'recharts'
import Link from 'next/link'
import { getTechWorkflowProgress, runTechDeliveryPlan } from '@/lib/actions/hcm'

export function OwnerDashboard() {
    const supabase = createClient()
    const [loading, setLoading] = useState(true)
    const [profile, setProfile] = useState(null)

    // Metrics
    const [empStats, setEmpStats] = useState({ total: 0, byDept: [] })
    const [okrAvg, setOkrAvg] = useState(0)
    const [topEmployees, setTopEmployees] = useState([])
    const [attendanceToday, setAttendanceToday] = useState({ present: 0, absent: 0 })
    const [techObjective, setTechObjective] = useState('Harden dev-qa-deploy flow for next release without schema changes')
    const [techLoading, setTechLoading] = useState(false)
    const [techResult, setTechResult] = useState(null)
    const [techProgress, setTechProgress] = useState(null)
    const [techError, setTechError] = useState('')

    useEffect(() => {
        async function load() {
            const { data: { user } } = await supabase.auth.getUser()
            const { data: prof, error: profErr } = await supabase
                .from('profiles').select('*, companies(name)').eq('id', user.id).single()
            
            if (prof && !profErr) {
                setProfile(prof)
            } else {
                setProfile({
                    id: user.id,
                    full_name: user.user_metadata?.full_name || 'Owner',
                    role: user.user_metadata?.role || 'owner',
                    company_id: user.user_metadata?.company_id || null,
                    companies: { name: user.user_metadata?.company_name || 'Perusahaan' },
                })
            }

            const cid = prof?.company_id || user.user_metadata?.company_id
            if (!cid) { setLoading(false); return }

            const [empRes, okrsRes, attRes] = await Promise.all([
                supabase.from('employees')
                    .select('id, department, profiles!inner(full_name)')
                    .eq('company_id', cid),
                supabase.from('okrs')
                    .select('id, employee_id, total_progress, employees(profiles!inner(full_name), department)')
                    .eq('company_id', cid),
                supabase.from('attendances')
                    .select('status')
                    .eq('company_id', cid)
                    .eq('date', new Date().toLocaleDateString('en-CA')),
            ])

            // Employees
            const emps = empRes.data || []
            const deptCount = {}
            emps.forEach(e => {
                const d = e.department || 'General'
                deptCount[d] = (deptCount[d] || 0) + 1
            })
            const byDept = Object.keys(deptCount).map(k => ({ name: k, value: deptCount[k] }))

            // OKRs
            const okrs = okrsRes.data || []
            const avg = okrs.length ? okrs.reduce((a, o) => a + (o.total_progress || 0), 0) / okrs.length : 0

            // Top employees based on average OKR progress
            const empOkrMap = {}
            okrs.forEach(o => {
                if (!empOkrMap[o.employee_id]) empOkrMap[o.employee_id] = { total: 0, count: 0, name: o.employees?.profiles?.full_name, dept: o.employees?.department }
                empOkrMap[o.employee_id].total += (o.total_progress || 0)
                empOkrMap[o.employee_id].count++
            })
            const topEmps = Object.values(empOkrMap)
                .map(v => ({ name: v.name, dept: v.dept, avg: Math.round(v.total / v.count) }))
                .sort((a, b) => b.avg - a.avg)
                .slice(0, 5)

            // Attendance
            const atts = attRes.data || []
            let present = 0, absent = 0
            atts.forEach(a => {
                if (['present', 'early_leave', 'holiday_present'].includes(a.status)) present++
                else absent++
            })

            setEmpStats({ total: emps.length, byDept })
            setOkrAvg(Math.round(avg))
            setTopEmployees(topEmps)
            setAttendanceToday({ present, absent: absent || (emps.length - present) }) // Rough estimation

            setLoading(false)

            try {
                const progress = await getTechWorkflowProgress({ companyId: cid })
                if (progress?.success) {
                    setTechProgress(progress.data)
                }
            } catch {
                // Optional panel; ignore when orchestrator is unavailable.
            }
        }
        load()
    }, [])

    async function handleRunTechPlan() {
        if (!profile?.company_id || !techObjective.trim()) return
        setTechLoading(true)
        setTechError('')
        try {
            const res = await runTechDeliveryPlan({
                companyId: profile.company_id,
                objective: techObjective,
            })
            setTechResult(res?.data || null)
            const progress = await getTechWorkflowProgress({ companyId: profile.company_id })
            if (progress?.success) {
                setTechProgress(progress.data)
            }
        } catch (err) {
            setTechError(err?.message || 'Failed to run tech delivery plan')
        } finally {
            setTechLoading(false)
        }
    }

    const COLORS = ['#ea580c', '#f97316', '#fb923c', '#fdba74', '#fed7aa', '#ffedd5']

    const dateStr = new Date().toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })

    return (
        <div className="space-y-8 pb-24">
            <Breadcrumbs />

            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
                <div>
                    <p className="text-xs font-bold text-muted-foreground mb-1">{dateStr}</p>
                    <h1 className="text-2xl md:text-3xl font-black text-foreground tracking-tight">
                        Executive Overview,{' '}
                        <span className="text-primary">{profile?.full_name?.split(' ')[0] ?? 'Owner'}</span>
                    </h1>
                    <p className="text-muted-foreground text-sm mt-1">{profile?.companies?.name ?? 'Perusahaan'} · Panel Eksekutif</p>
                </div>
            </div>

            {/* Main Stats Row */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
                {[
                    { label: 'Total Karyawan', value: empStats.total, icon: Users, bg: 'bg-primary/10', color: 'text-primary' },
                    { label: 'Rata-rata Target Tercapai', value: `${okrAvg}%`, icon: Target, bg: 'bg-emerald-100', color: 'text-emerald-600' },
                    { label: 'Hadir Hari Ini', value: attendanceToday.present, sub: `dari ${empStats.total}`, icon: Clock, bg: 'bg-blue-100', color: 'text-blue-600' },
                    { label: 'Departemen Aktif', value: empStats.byDept.length, icon: Building2, bg: 'bg-violet-100', color: 'text-violet-600' },
                ].map((s, i) => (
                    <Card key={i} className="p-6 border-none shadow-sm rounded-3xl hover:shadow-md transition-all flex flex-col justify-between">
                        <div className="flex items-center gap-3 mb-4">
                            <div className={`w-10 h-10 ${s.bg} rounded-xl flex items-center justify-center shrink-0`}>
                                <s.icon className={`w-5 h-5 ${s.color}`} />
                            </div>
                            <p className="text-[10px] font-black text-muted-foreground uppercase tracking-widest leading-tight">{s.label}</p>
                        </div>
                        {loading ? <Skeleton className="h-8 w-16" /> : (
                            <div className="flex items-end gap-2">
                                <p className="text-3xl font-black text-foreground leading-none">{s.value}</p>
                                {s.sub && <p className="text-xs font-bold text-muted-foreground mb-1">{s.sub}</p>}
                            </div>
                        )}
                    </Card>
                ))}
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-8">
                {/* Distribusi Karyawan (Pie Chart) */}
                <Card className="p-8 border-none shadow-sm rounded-3xl flex flex-col justify-between">
                    <div>
                        <h2 className="text-[10px] font-black text-muted-foreground uppercase tracking-widest mb-2 flex items-center gap-2">
                            <Users className="w-3.5 h-3.5" /> Distribusi Departemen
                        </h2>
                        <p className="text-sm font-medium text-foreground mb-6">Sebaran tenaga kerja berdasarkan departemen.</p>
                    </div>
                    {loading ? <Skeleton className="h-[200px] w-full" /> : empStats.byDept.length === 0 ? (
                        <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground py-8">Belum ada data struktur departemen.</div>
                    ) : (
                        <div className="flex items-center gap-4 flex-1">
                            <ResponsiveContainer width={150} height={150}>
                                <PieChart>
                                    <Pie data={empStats.byDept} cx="50%" cy="50%" innerRadius={45} outerRadius={60} strokeWidth={0} dataKey="value">
                                        {empStats.byDept.map((entry, idx) => (
                                            <Cell key={`cell-${idx}`} fill={COLORS[idx % COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <RechartsTooltip 
                                        wrapperClassName="!text-xs !bg-white !border-none !shadow-xl !rounded-xl"
                                        formatter={(value) => [`${value} Karyawan`]}
                                    />
                                </PieChart>
                            </ResponsiveContainer>
                            <div className="flex-1 space-y-2">
                                {empStats.byDept.map((dept, idx) => (
                                    <div key={idx} className="flex items-center justify-between text-xs">
                                        <div className="flex items-center gap-2">
                                            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }} />
                                            <span className="font-bold text-muted-foreground truncate max-w-[100px]">{dept.name}</span>
                                        </div>
                                        <span className="font-black text-foreground">{dept.value}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </Card>

                {/* Top Performers */}
                <Card className="p-8 border-none shadow-sm rounded-3xl">
                    <div className="flex items-center justify-between mb-6">
                        <div>
                            <h2 className="text-[10px] font-black text-muted-foreground uppercase tracking-widest mb-1 flex items-center gap-2">
                                <TrendingUp className="w-3.5 h-3.5" /> Top Performers (OKR)
                            </h2>
                            <p className="text-sm font-medium text-foreground">Karyawan dengan pencapaian OKR tertinggi.</p>
                        </div>
                    </div>
                    {loading ? (
                        <div className="space-y-4">
                            {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
                        </div>
                    ) : topEmployees.length === 0 ? (
                        <div className="flex flex-col items-center justify-center text-muted-foreground py-10 h-full">
                            <Activity className="w-8 h-8 md:mb-2 opacity-50" />
                            <p className="text-sm font-medium">Belum ada data OKR yang berjalan bernilai aktif.</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {topEmployees.map((emp, idx) => (
                                <div key={idx} className="flex items-center justify-between group">
                                    <div className="flex items-center gap-4">
                                        <div className="w-8 h-8 rounded-full bg-brand-50 text-primary flex items-center justify-center font-black text-xs shrink-0">
                                            {idx + 1}
                                        </div>
                                        <div>
                                            <p className="text-sm font-bold text-foreground group-hover:text-primary transition-colors">{emp.name}</p>
                                            <p className="text-[10px] font-black text-muted-foreground uppercase tracking-wider">{emp.dept || 'General'}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className="w-24 h-2 bg-slate-100 rounded-full overflow-hidden hidden sm:block">
                                            <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${emp.avg}%` }} />
                                        </div>
                                        <Badge variant="secondary" className="bg-emerald-50 text-emerald-700 font-black text-xs min-w-[3rem] justify-center">
                                            {emp.avg}%
                                        </Badge>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </Card>
            </div>

            <Card className="p-8 border-none shadow-sm rounded-3xl space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <div>
                        <h2 className="text-[10px] font-black text-muted-foreground uppercase tracking-widest mb-1">AI Tech Workflow (Dev to QA to Deploy)</h2>
                        <p className="text-sm font-medium text-foreground">Jalankan CTO orchestration plan langsung dari dashboard.</p>
                    </div>
                    <Badge variant="secondary" className="w-fit">No schema change</Badge>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
                    <Card className="p-4 rounded-2xl border">
                        <p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Runs</p>
                        <p className="text-2xl font-black">{techProgress?.runsCount ?? 0}</p>
                    </Card>
                    <Card className="p-4 rounded-2xl border">
                        <p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Tickets</p>
                        <p className="text-2xl font-black">{techProgress?.ticketsCount ?? 0}</p>
                    </Card>
                    <Card className="p-4 rounded-2xl border">
                        <p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">DoD Pass</p>
                        <p className="text-2xl font-black">{techProgress?.dodPassRate ?? 0}%</p>
                    </Card>
                    <Card className="p-4 rounded-2xl border">
                        <p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Avg Duration</p>
                        <p className="text-2xl font-black">{techProgress?.avgDurationSec ?? 0}s</p>
                    </Card>
                    <Card className="p-4 rounded-2xl border">
                        <p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Latest Run</p>
                        <p className="text-sm font-black break-all">{techProgress?.latestRunId ?? '-'}</p>
                    </Card>
                </div>

                <div className="space-y-3">
                    <label className="text-xs font-black uppercase tracking-widest text-muted-foreground">Objective</label>
                    <textarea
                        className="w-full min-h-28 rounded-2xl border bg-white p-4 text-sm"
                        value={techObjective}
                        onChange={(e) => setTechObjective(e.target.value)}
                        placeholder="Write technical objective for CTO planning..."
                    />
                    <div className="flex items-center gap-3">
                        <button
                            type="button"
                            onClick={handleRunTechPlan}
                            disabled={techLoading || !profile?.company_id}
                            className="px-5 py-2 rounded-xl bg-slate-900 text-white text-sm font-bold disabled:opacity-60"
                        >
                            {techLoading ? 'Running...' : 'Run Tech Delivery Plan'}
                        </button>
                        {techError ? <p className="text-xs font-bold text-rose-600">{techError}</p> : null}
                    </div>
                </div>

                {techResult ? (
                    <div className="rounded-2xl border p-4 bg-slate-50 space-y-2">
                        <p className="text-xs font-black uppercase tracking-widest text-muted-foreground">Latest Execution</p>
                        <p className="text-sm"><span className="font-bold">Run ID:</span> {techResult.run_id || '-'}</p>
                        <p className="text-sm break-all"><span className="font-bold">Report:</span> {techResult.combined_report || '-'}</p>
                    </div>
                ) : null}

                {techProgress?.latestTickets?.length ? (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-left text-xs uppercase tracking-widest text-muted-foreground">
                                    <th className="py-2">Ticket</th>
                                    <th className="py-2">Agent</th>
                                    <th className="py-2">DoD</th>
                                    <th className="py-2">Duration</th>
                                </tr>
                            </thead>
                            <tbody>
                                {techProgress.latestTickets.map((t) => (
                                    <tr key={t.ticket_id} className="border-t">
                                        <td className="py-2 font-medium">{t.ticket_id}</td>
                                        <td className="py-2">{t.agent_id}</td>
                                        <td className="py-2">{t?.dod?.status || '-'}</td>
                                        <td className="py-2">{t.duration_seconds || 0}s</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : null}
            </Card>
        </div>
    )
}
