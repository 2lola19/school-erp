"use client";

import { useEffect, useState } from "react";

interface TelemetryData {
  teachers: number;
  students: number;
  classrooms: number;
  enrollments: number;
}

export default function DashboardStats() {
  const [stats, setStats] = useState<TelemetryData>({
    teachers: 0,
    students: 0,
    classrooms: 0,
    enrollments: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/v1/dashboard/stats")
      .then((res) => res.json())
      .then((data) => {
        setStats(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("[-] Telemetry stream failed:", err);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="p-4 text-gray-500">Syncing telemetry...</div>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <StatCard title="Total Teachers" value={stats.teachers} color="border-blue-500" />
      <StatCard title="Total Students" value={stats.students} color="border-green-500" />
      <StatCard title="Active Classrooms" value={stats.classrooms} color="border-purple-500" />
      <StatCard title="Total Enrollments" value={stats.enrollments} color="border-orange-500" />
    </div>
  );
}

function StatCard({ title, value, color }: { title: string; value: number; color: string }) {
  return (
    <div className={`bg-white p-6 rounded-lg shadow-sm border-l-4 ${color}`}>
      <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">{title}</h3>
      <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
    </div>
  );
}