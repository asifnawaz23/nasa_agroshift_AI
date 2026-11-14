import { useState } from 'react';
import { Link } from 'react-router-dom';
import FarmMap from "../components/FarmMap";
import FarmerInputForm from "../components/FarmerInputForm";

export default function Dashboard() {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [farmLocation, setFarmLocation] = useState(null);

    const stats = [
        { name: 'Total Users', value: '12,450', change: '+12.5%', positive: true },
        { name: 'Active Sessions', value: '1,234', change: '+5.2%', positive: true },
        { name: 'Revenue', value: '$48,290', change: '+18.1%', positive: true },
        { name: 'Pending Issues', value: '14', change: '-2.4%', positive: false },
    ];

    const recentActivity = [
        { id: 1, user: 'Sarah Jenkins', action: 'Created a new project', status: 'Completed', date: '2 mins ago' },
        { id: 2, user: 'Michael Chen', action: 'Updated billing details', status: 'Pending', date: '1 hour ago' },
        { id: 3, user: 'Ayesha Khan', action: 'Invited 3 team members', status: 'Completed', date: '3 hours ago' },
        { id: 4, user: 'David Ross', action: 'Exported monthly report', status: 'Completed', date: '5 hours ago' },
    ];

    const handleFarmSubmit = (farmData) => {
        console.log("Farmer submitted data:", farmData);

        // Next step: send farmData to your backend API
    };

    return (
        <div className="min-h-screen bg-gray-50 flex">
            {/* Mobile Sidebar Backdrop */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 z-20 bg-black/50 lg:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside
                className={`fixed inset-y-0 left-0 z-30 w-64 bg-slate-900 text-white transform transition-transform duration-200 ease-in-out lg:translate-x-0 lg:static lg:inset-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'
                    }`}
            >
                <div className="flex items-center justify-between h-16 px-6 bg-slate-950">
                    <span className="text-xl font-bold tracking-wider text-indigo-400">AppPanel</span>
                    <button
                        className="lg:hidden text-gray-400 hover:text-white"
                        onClick={() => setSidebarOpen(false)}
                    >
                        ✕
                    </button>
                </div>

                <nav className="px-4 py-6 space-y-2">
                    <Link
                        to="/dashboard"
                        className="flex items-center px-4 py-2.5 text-sm font-medium rounded-lg bg-indigo-600 text-white"
                    >
                        Overview
                    </Link>
                    <a
                        href="#analytics"
                        className="flex items-center px-4 py-2.5 text-sm font-medium text-gray-300 rounded-lg hover:bg-slate-800 hover:text-white transition"
                    >
                        Analytics
                    </a>
                    <a
                        href="#users"
                        className="flex items-center px-4 py-2.5 text-sm font-medium text-gray-300 rounded-lg hover:bg-slate-800 hover:text-white transition"
                    >
                        Users
                    </a>
                    <a
                        href="#settings"
                        className="flex items-center px-4 py-2.5 text-sm font-medium text-gray-300 rounded-lg hover:bg-slate-800 hover:text-white transition"
                    >
                        Settings
                    </a>
                </nav>

                <div className="absolute bottom-0 w-full p-4 border-t border-slate-800">
                    <Link
                        to="/login"
                        className="flex items-center justify-center w-full px-4 py-2 text-sm font-medium text-gray-300 bg-slate-800 rounded-lg hover:bg-red-600 hover:text-white transition"
                    >
                        Sign Out
                    </Link>
                </div>
            </aside>

            {/* Main Content */}
            <div className="flex-1 flex flex-col min-w-0">
                {/* Top Navbar */}
                <header className="flex items-center justify-between h-16 px-6 bg-white border-b border-gray-200">
                    <div className="flex items-center gap-4">
                        <button
                            className="lg:hidden text-gray-600 hover:text-gray-900 focus:outline-none"
                            onClick={() => setSidebarOpen(true)}
                        >
                            ☰
                        </button>
                        <input
                            type="text"
                            placeholder="Search..."
                            className="hidden sm:block w-64 px-3 py-1.5 text-sm bg-gray-100 border border-transparent rounded-lg focus:bg-white focus:border-indigo-500 focus:outline-none"
                        />
                    </div>

                    <div className="flex items-center gap-4">
                        <span className="text-sm font-medium text-gray-700">Alex Morgan</span>
                        <div className="w-9 h-9 rounded-full bg-indigo-600 text-white flex items-center justify-center font-semibold text-sm">
                            AM
                        </div>
                    </div>
                </header>

                {/* Dashboard Body */}
                <main className="flex-1 p-6 space-y-6">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">Dashboard Overview</h1>
                            <p className="text-sm text-gray-500">Welcome back! Here is what is happening today.</p>
                        </div>
                        <button className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition self-start sm:self-auto">
                            + New Report
                        </button>
                    </div>


                    <FarmMap
                        onLocationSelect={(location) => {
                            setFarmLocation(location);
                        }}
                    />
                    <FarmerInputForm
                        location={farmLocation}
                        onSubmit={handleFarmSubmit}
                    />

                    {/* Stats Grid */}
                    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-4">
                        {stats.map((stat) => (
                            <div
                                key={stat.name}
                                className="p-6 bg-white border border-gray-200 rounded-xl shadow-xs"
                            >
                                <p className="text-sm font-medium text-gray-500">{stat.name}</p>
                                <div className="flex items-baseline justify-between mt-2">
                                    <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                                    <span
                                        className={`text-xs font-semibold px-2 py-0.5 rounded-full ${stat.positive
                                                ? 'bg-emerald-50 text-emerald-700'
                                                : 'bg-rose-50 text-rose-700'
                                            }`}
                                    >
                                        {stat.change}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Recent Activity Table */}
                    <div className="bg-white border border-gray-200 rounded-xl shadow-xs overflow-hidden">
                        <div className="px-6 py-4 border-b border-gray-200">
                            <h2 className="text-base font-semibold text-gray-900">Recent Activity</h2>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="text-xs font-semibold text-gray-500 uppercase bg-gray-50 border-b border-gray-200">
                                        <th className="px-6 py-3">User</th>
                                        <th className="px-6 py-3">Action</th>
                                        <th className="px-6 py-3">Status</th>
                                        <th className="px-6 py-3">Time</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200 text-sm">
                                    {recentActivity.map((item) => (
                                        <tr key={item.id} className="hover:bg-gray-50 transition">
                                            <td className="px-6 py-4 font-medium text-gray-900">{item.user}</td>
                                            <td className="px-6 py-4 text-gray-600">{item.action}</td>
                                            <td className="px-6 py-4">
                                                <span
                                                    className={`inline-flex px-2.5 py-0.5 text-xs font-medium rounded-full ${item.status === 'Completed'
                                                            ? 'bg-emerald-100 text-emerald-800'
                                                            : 'bg-amber-100 text-amber-800'
                                                        }`}
                                                >
                                                    {item.status}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-gray-500">{item.date}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}