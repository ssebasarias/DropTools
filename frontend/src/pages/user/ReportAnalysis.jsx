import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { Download, Calendar, DollarSign, CheckCircle, XCircle, Clock, Mail, Key } from 'lucide-react';
import SubscriptionGate from '../../components/common/SubscriptionGate';

const ReportAnalysis = () => {
    const [downloadConfig, setDownloadConfig] = useState({
        email: '',
        password: '',
        downloadTime: '23:00'
    });

    // Mock Data for Charts
    const monthlyData = [
        { name: 'Week 1', income: 4000, orders: 24 },
        { name: 'Week 2', income: 3000, orders: 18 },
        { name: 'Week 3', income: 5000, orders: 29 },
        { name: 'Week 4', income: 2780, orders: 15 },
    ];

    return (
        <SubscriptionGate minTier="SILVER" title="Report Analysis (requiere SILVER)">
        <div style={{ padding: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                    <h1>Report Analysis</h1>
                    <p className="text-muted">Insights from your latest order reports.</p>
                </div>
                <button className="btn-primary" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <Download size={18} /> Download Latest Report
                </button>
            </div>

            {/* Configuration Section */}
            <div className="glass-card" style={{ marginBottom: '2rem' }}>
                <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Calendar size={20} className="text-primary" /> Download Scheduler & Credentials
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem' }}>
                    <div className="form-group">
                        <label className="form-label">Secondary Account Email</label>
                        <div style={{ position: 'relative' }}>
                            <Mail size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                            <input
                                type="email"
                                className="glass-input"
                                style={{ paddingLeft: '38px' }}
                                placeholder="reporter@yourdomain.com"
                                value={downloadConfig.email}
                                onChange={(e) => setDownloadConfig({ ...downloadConfig, email: e.target.value })}
                            />
                        </div>
                    </div>
                    <div className="form-group">
                        <label className="form-label">Password</label>
                        <div style={{ position: 'relative' }}>
                            <Key size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                            <input
                                type="password"
                                className="glass-input"
                                style={{ paddingLeft: '38px' }}
                                placeholder="•••••••••"
                                value={downloadConfig.password}
                                onChange={(e) => setDownloadConfig({ ...downloadConfig, password: e.target.value })}
                            />
                        </div>
                    </div>
                    <div className="form-group">
                        <label className="form-label">Download Time</label>
                        <div style={{ position: 'relative' }}>
                            <Clock size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                            <input
                                type="time"
                                className="glass-input"
                                style={{ paddingLeft: '38px' }}
                                value={downloadConfig.downloadTime}
                                onChange={(e) => setDownloadConfig({ ...downloadConfig, downloadTime: e.target.value })}
                            />
                        </div>
                    </div>
                </div>
                <p className="text-muted" style={{ fontSize: '0.85rem', marginTop: '1rem' }}>
                    * Reports will be downloaded for the current day and the previous 2 days to track order movement.
                </p>
            </div>

            {/* KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
                <div className="glass-card" style={{ background: 'linear-gradient(145deg, rgba(99,102,241,0.1), rgba(255,255,255,0.03))' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                        <span className="text-muted">Total Revenue</span>
                        <div style={{ padding: '0.5rem', background: 'rgba(99,102,241,0.2)', borderRadius: '8px' }}>
                            <DollarSign size={20} className="text-primary" />
                        </div>
                    </div>
                    <h2 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>$14,780</h2>
                    <span className="text-muted" style={{ fontSize: '0.9rem' }}>+12% from last month</span>
                </div>

                <div className="glass-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                        <span className="text-muted">Accepted Orders</span>
                        <div style={{ padding: '0.5rem', background: 'rgba(16,185,129,0.2)', borderRadius: '8px' }}>
                            <CheckCircle size={20} style={{ color: 'var(--success)' }} />
                        </div>
                    </div>
                    <h2 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>86</h2>
                    <span className="text-muted" style={{ fontSize: '0.9rem' }}>92% acceptance rate</span>
                </div>

                <div className="glass-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                        <span className="text-muted">Cancelled Orders</span>
                        <div style={{ padding: '0.5rem', background: 'rgba(239,68,68,0.2)', borderRadius: '8px' }}>
                            <XCircle size={20} style={{ color: 'var(--danger)' }} />
                        </div>
                    </div>
                    <h2 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>8</h2>
                    <span className="text-muted" style={{ fontSize: '0.9rem' }}>Low cancellation rate</span>
                </div>
            </div>

            {/* Charts */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.5rem' }}>
                <div className="glass-card">
                    <h3 style={{ marginBottom: '1.5rem' }}>Monthly Revenue Progress</h3>
                    <div style={{ height: '300px', width: '100%' }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={monthlyData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                                <XAxis dataKey="name" stroke="#94a3b8" axisLine={false} tickLine={false} />
                                <YAxis stroke="#94a3b8" axisLine={false} tickLine={false} tickFormatter={(value) => `$${value}`} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#09090b', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px' }}
                                    itemStyle={{ color: '#fff' }}
                                />
                                <Bar dataKey="income" fill="#6366f1" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="glass-card">
                    <h3 style={{ marginBottom: '1.5rem' }}>Order Volume Trend</h3>
                    <div style={{ height: '300px', width: '100%' }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={monthlyData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                                <XAxis dataKey="name" stroke="#94a3b8" axisLine={false} tickLine={false} />
                                <YAxis stroke="#94a3b8" axisLine={false} tickLine={false} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#09090b', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px' }}
                                    itemStyle={{ color: '#fff' }}
                                />
                                <Line type="monotone" dataKey="orders" stroke="#ec4899" strokeWidth={3} dot={{ r: 4, fill: '#ec4899' }} activeDot={{ r: 6 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
        </SubscriptionGate>
    );
};

export default ReportAnalysis;
