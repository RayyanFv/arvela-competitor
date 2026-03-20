'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase/client'
import {
    ShieldCheck, Users, Mail, UserPlus,
    Building2, KeyRound
} from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Breadcrumbs } from '@/components/layout/Breadcrumbs'
import Link from 'next/link'
import { ROLE_LABELS, ROLES } from '@/lib/constants/roles'
import { getTechWorkflowProgress, runTechDeliveryPlan } from '@/lib/actions/hcm'

export function SuperAdminDashboard() {
    const supabase = createClient()
    const [loading, setLoading] = useState(true)
    const [profile, setProfile] = useState(null)
    const [stats, setStats] = useState({ profiles: 0, employees: 0, roles: {} })
    const [recentUsers, setRecentUsers] = useState([])
    const [techObjective, setTechObjective] = useState('Harden dev-qa-deploy flow for next release without schema changes')
    const [techLoading, setTechLoading] = useState(false)
    const [techResult, setTechResult] = useState(null)
    const [techProgress, setTechProgress] = useState(null)
    const [techError, setTechError] = useState('')

    useEffect(() => {
        async function load() {
            const { data: { user } } = await supabase.auth.getUser()
            
            // Try profile query with company join
            const { data: prof, error: profErr } = await supabase
                .from('profiles').select('*, companies(name)').eq('id', user.id).single()
            
            if (prof && !profErr) {
                setProfile(prof)
            } else {
                // Fallback to metadata
                setProfile({
                    id: user.id,
                    full_name: user.user_metadata?.full_name || 'Admin',
                    role: user.user_metadata?.role || 'super_admin',
                    company_id: user.user_metadata?.company_id || null,
                    companies: { name: user.user_metadata?.company_name || 'Perusahaan' },
                })
            }

            const cid = prof?.company_id || user.user_metadata?.company_id
            if (!cid) { setLoading(false); return }

            const [profRes, empRes] = await Promise.all([
                supabase.from('profiles')
                    .select('id, full_name, email, role, created_at')
                    .eq('company_id', cid)
                    .order('created_at', { ascending: false }),
                supabase.from('employees')
                    .select('id', { count: 'exact', head: true })
                    .eq('company_id', cid)
            ])

            const users = profRes.data || []
            const rolesCount = {}
            Object.values(ROLES).forEach(r => rolesCount[r] = 0)
            
            users.forEach(u => {
                const r = u.role || 'user'
                if (rolesCount[r] !== undefined) rolesCount[r]++
            })

            setStats({
                profiles: users.length,
                employees: empRes.count || 0,
                roles: rolesCount
            })
            setRecentUsers(users.slice(0, 8))

            try {
                const progress = await getTechWorkflowProgress({ companyId: cid })
                if (progress?.success) {
                    setTechProgress(progress.data)
                }
            } catch {
                // Optional panel; ignore when orchestrator is unavailable.
            }
            setLoading(false)
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

    const getRoleBadgeColor = (role) => {
        switch (role) {
            case ROLES.SUPER_ADMIN: return 'bg-rose-100 text-rose-700 border-rose-200'
            case ROLES.OWNER: return 'bg-amber-100 text-amber-700 border-amber-200'
            case ROLES.HR_ADMIN: return 'bg-violet-100 text-violet-700 border-violet-200'
            case ROLES.EMPLOYEE: return 'bg-emerald-100 text-emerald-700 border-emerald-200'
            case ROLES.CANDIDATE: return 'bg-blue-100 text-blue-700 border-blue-200'
            default: return 'bg-slate-100 text-slate-700 border-slate-200'
        }
    }

    return (
        <div className="space-y-8 pb-24 animate-in slide-in-from-bottom-4 duration-700">
            <Breadcrumbs />

            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
                <div>
                    <h1 className="text-2xl md:text-3xl font-black text-foreground tracking-tight flex items-center gap-3">
                        <ShieldCheck className="w-8 h-8 text-rose-500" /> System Control Panel
                    </h1>
                    <p className="text-muted-foreground text-sm mt-1 mb-2 max-w-lg">
                        Pusat kendali hak akses. Daftarkan akun Administrator HR dan Eksekutif untuk <strong className="text-foreground">{profile?.companies?.name ?? 'Perusahaan'}</strong>.
                    </p>
                </div>
                <Link href="/dashboard/settings/users">
                    <Button className="h-10 px-5 rounded-xl bg-foreground hover:bg-slate-800 text-background font-bold gap-2">
                        <UserPlus className="w-4 h-4" /> Daftarkan Pengguna Baru
                    </Button>
                </Link>
            </div>

            {/* System Status Row */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
                {[
                    { label: 'Total Akun Sistem', value: stats.profiles, icon: Users, color: 'text-blue-500', bg: 'bg-blue-50' },
                    { label: 'Karyawan Terhubung', value: stats.employees, icon: Building2, color: 'text-emerald-500', bg: 'bg-emerald-50' },
                    { label: 'HR Administrator', value: stats.roles[ROLES.HR_ADMIN], icon: KeyRound, color: 'text-violet-500', bg: 'bg-violet-50' },
                    { label: 'Pemilik (Owner)', value: stats.roles[ROLES.OWNER], icon: ShieldCheck, color: 'text-amber-500', bg: 'bg-amber-50' },
                ].map((s, i) => (
                    <Card key={i} className="p-6 border-none shadow-sm rounded-3xl hover:shadow-md transition-all">
                        <div className="flex items-center gap-3 mb-4">
                            <div className={`w-10 h-10 flex flex-col items-center justify-center rounded-xl shrink-0 ${s.bg}`}>
                                <s.icon className={`w-5 h-5 ${s.color}`} />
                            </div>
                            <p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">{s.label}</p>
                        </div>
                        {loading ? <Skeleton className="h-8 w-14" /> : <p className="text-3xl font-black">{s.value}</p>}
                    </Card>
                ))}
            </div>

            {/* User Directory */}
            <Card className="p-6 md:p-8 border-none shadow-sm rounded-3xl space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <div>
                        <h2 className="text-[10px] font-black text-muted-foreground uppercase tracking-widest mb-1">AI Tech Workflow (Super Admin)</h2>
                        <p className="text-sm font-medium text-foreground">Jalankan CTO orchestration plan langsung dari control panel.</p>
                    </div>
                    <Badge variant="secondary" className="w-fit">No schema change</Badge>
                </div>

                <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
                    <Card className="p-4 rounded-2xl border"><p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Runs</p><p className="text-2xl font-black">{techProgress?.runsCount ?? 0}</p></Card>
                    <Card className="p-4 rounded-2xl border"><p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Tickets</p><p className="text-2xl font-black">{techProgress?.ticketsCount ?? 0}</p></Card>
                    <Card className="p-4 rounded-2xl border"><p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">DoD Pass</p><p className="text-2xl font-black">{techProgress?.dodPassRate ?? 0}%</p></Card>
                    <Card className="p-4 rounded-2xl border"><p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Avg Duration</p><p className="text-2xl font-black">{techProgress?.avgDurationSec ?? 0}s</p></Card>
                    <Card className="p-4 rounded-2xl border"><p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Latest Run</p><p className="text-sm font-black break-all">{techProgress?.latestRunId ?? '-'}</p></Card>
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
            </Card>

            <Card className="p-6 md:p-8 border-none shadow-sm rounded-3xl">
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h2 className="text-sm font-black text-foreground uppercase tracking-widest">Aktivitas Akun Terbaru</h2>
                        <p className="text-xs font-medium text-muted-foreground mt-1">Daftar profil pengguna yang baru dibuat / terdaftar ke perusahaan ini.</p>
                    </div>
                    <Link href="/dashboard/settings/users">
                        <Button variant="ghost" size="sm" className="text-primary font-bold hover:bg-brand-50">Kelola Semua Akses</Button>
                    </Link>
                </div>

                {loading ? (
                    <div className="space-y-4">
                        {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-14 w-full rounded-2xl" />)}
                    </div>
                ) : recentUsers.length === 0 ? (
                    <div className="py-12 text-center border-dashed border-2 border-slate-100 rounded-3xl">
                        <Users className="w-10 h-10 text-muted mx-auto mb-3" />
                        <p className="text-sm font-bold text-muted-foreground">Tidak ada pengguna terdeteksi.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {recentUsers.map(u => (
                            <div key={u.id} className="flex flex-col sm:flex-row sm:items-center justify-between p-4 bg-slate-50 border border-slate-100 rounded-2xl hover:bg-white hover:border-slate-200 transition-all gap-4 group">
                                <div className="flex items-center gap-4 min-w-0">
                                    <div className="w-10 h-10 bg-white border border-slate-200 rounded-xl flex items-center justify-center font-black text-slate-400 group-hover:text-primary transition-colors shrink-0">
                                        {u.full_name?.charAt(0)}
                                    </div>
                                    <div className="min-w-0">
                                        <h4 className="font-bold text-foreground text-sm truncate">{u.full_name}</h4>
                                        <p className="text-[10px] font-bold text-muted-foreground truncate flex items-center gap-1.5 mt-0.5">
                                            <Mail className="w-3 h-3 text-slate-300" /> {u.email}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3 justify-end sm:shrink-0 ml-14 sm:ml-0">
                                    <Badge variant="outline" className={`px-2.5 py-0.5 text-[9px] font-black uppercase tracking-wider rounded-md border text-center ${getRoleBadgeColor(u.role)}`}>
                                        {ROLE_LABELS[u.role] || u.role}
                                    </Badge>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </Card>
        </div>
    )
}
