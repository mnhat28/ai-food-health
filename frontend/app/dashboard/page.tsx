"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { logsApi, adviceApi } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import { format, startOfWeek, subWeeks } from "date-fns";
import {
  ArrowLeft,
  RefreshCw,
  TrendingUp,
  Calendar,
  Target,
  Award,
} from "lucide-react";
import CalorieChart from "@/components/CalorieChart";
import NutritionBadge from "@/components/NutritionBadge";

// ==========================================
// Types
// ==========================================

interface DailySummary {
  date: string;
  total_calories: number;
  total_protein: number;
  total_carbohydrates: number;
  total_fat: number;
  calorie_goal: number | null;
  goal_percentage: number | null;
}

interface WeeklySummary {
  week_start: string;
  week_end: string;
  daily_summaries: DailySummary[];
  avg_calories: number;
  avg_protein: number;
  avg_carbohydrates: number;
  avg_fat: number;
  calorie_goal: number | null;
}

interface WeeklyReport {
  report: string;
  week_start: string;
  week_end: string;
  days_logged: number;
  generated_at: string;
}

// ==========================================
// Stat card
// ==========================================

function StatCard({
  icon,
  label,
  value,
  sub,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  color: string;
}) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-4">
      <div className={`w-8 h-8 rounded-xl flex items-center justify-center mb-3 ${color}`}>
        {icon}
      </div>
      <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">
        {label}
      </p>
      <p className="text-xl font-bold text-gray-800 mt-0.5">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

// ==========================================
// Week selector
// ==========================================

function WeekSelector({
  currentWeek,
  onChange,
}: {
  currentWeek: Date;
  onChange: (week: Date) => void;
}) {
  return (
    <div className="flex items-center justify-between bg-white rounded-2xl border border-gray-100 px-4 py-3">
      <button
        onClick={() => onChange(subWeeks(currentWeek, 1))}
        className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
      </button>
      <div className="text-center">
        <p className="text-sm font-semibold text-gray-700">
          {format(currentWeek, "MMM d")} —{" "}
          {format(
            new Date(currentWeek.getTime() + 6 * 24 * 60 * 60 * 1000),
            "MMM d, yyyy"
          )}
        </p>
        <p className="text-xs text-gray-400 mt-0.5">
          {format(currentWeek, "'Week' w, yyyy")}
        </p>
      </div>
      <button
        onClick={() => onChange(subWeeks(currentWeek, -1))}
        disabled={currentWeek >= startOfWeek(new Date())}
        className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors disabled:opacity-30"
      >
        <ArrowLeft className="w-4 h-4 rotate-180" />
      </button>
    </div>
  );
}

// ==========================================
// AI weekly report
// ==========================================

function WeeklyReportCard({
  report,
  daysLogged,
  loading,
  onRefresh,
}: {
  report: WeeklyReport | null;
  daysLogged?: number;
  loading: boolean;
  onRefresh: () => void;
}) {
  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-gray-100 p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-700">AI Weekly Report</h3>
        </div>
        <div className="space-y-2 animate-pulse">
          <div className="h-3 bg-gray-100 rounded-full w-full" />
          <div className="h-3 bg-gray-100 rounded-full w-5/6" />
          <div className="h-3 bg-gray-100 rounded-full w-4/6" />
          <div className="h-3 bg-gray-100 rounded-full w-5/6" />
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="bg-white rounded-2xl border border-gray-100 p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-700">AI Weekly Report</h3>
          <button
            onClick={onRefresh}
            className="flex items-center gap-1.5 text-xs text-primary-600 hover:text-primary-700 font-medium"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Generate
          </button>
        </div>
        <div className="flex flex-col items-center py-6 text-center">
          <span className="text-3xl mb-2">📊</span>
          <p className="text-sm text-gray-500">
            Log at least 3 days of meals to generate your weekly AI report
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-700">AI Weekly Report</h3>
          {daysLogged !== undefined && (
            <p className="text-xs text-gray-400 mt-0.5">
              Based on {daysLogged} days of data
            </p>
          )}
        </div>
        <button
          onClick={onRefresh}
          className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="bg-gradient-to-br from-primary-50 to-emerald-50 border border-primary-100 rounded-xl p-4">
        <div className="flex gap-2 mb-2">
          <span className="text-lg">🤖</span>
          <p className="text-xs font-semibold text-primary-700 uppercase tracking-wide">
            Claude AI Analysis
          </p>
        </div>
        <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
          {report.report}
        </p>
        <p className="text-xs text-gray-400 mt-3">
          Generated {format(new Date(report.generated_at), "MMM d 'at' h:mm a")}
        </p>
      </div>
    </div>
  );
}

// ==========================================
// Days logged tracker
// ==========================================

function DaysLoggedTracker({ dailySummaries }: { dailySummaries: DailySummary[] }) {
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-4">
      <h3 className="font-semibold text-gray-700 mb-3">Days Logged</h3>
      <div className="flex gap-2 justify-between">
        {dailySummaries.map((summary, index) => {
          const hasData = summary.total_calories > 0;
          const pct = summary.goal_percentage;
          const color = hasData
            ? pct && pct >= 90
              ? "bg-primary-500"
              : pct && pct >= 50
              ? "bg-yellow-400"
              : "bg-blue-400"
            : "bg-gray-100";

          return (
            <div key={index} className="flex flex-col items-center gap-1.5">
              <div
                className={`w-8 h-8 rounded-xl ${color} flex items-center justify-center transition-all`}
                title={`${summary.date}: ${Math.round(summary.total_calories)} kcal`}
              >
                {hasData && (
                  <span className="text-white text-xs font-bold">
                    {Math.round(summary.total_calories / 100)}
                  </span>
                )}
              </div>
              <span className="text-xs text-gray-400">{days[index]}</span>
            </div>
          );
        })}
      </div>
      <div className="flex items-center gap-3 mt-3 pt-3 border-t border-gray-100">
        {[
          { color: "bg-primary-500", label: "On track" },
          { color: "bg-yellow-400", label: "Partial" },
          { color: "bg-blue-400", label: "Low" },
          { color: "bg-gray-100", label: "No data" },
        ].map((item) => (
          <div key={item.label} className="flex items-center gap-1">
            <span className={`w-2.5 h-2.5 rounded-sm ${item.color}`} />
            <span className="text-xs text-gray-400">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ==========================================
// Main page
// ==========================================

export default function DashboardPage() {
  const router = useRouter();
  const [currentWeek, setCurrentWeek] = useState<Date>(
    startOfWeek(new Date(), { weekStartsOn: 1 })
  );
  const [weeklySummary, setWeeklySummary] = useState<WeeklySummary | null>(null);
  const [weeklyReport, setWeeklyReport] = useState<WeeklyReport | null>(null);
  const [loadingData, setLoadingData] = useState(true);
  const [loadingReport, setLoadingReport] = useState(false);

  // ==========================================
  // Auth guard
  // ==========================================

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/auth/login");
    }
  }, [router]);

  // ==========================================
  // Fetch weekly data
  // ==========================================

  const fetchWeeklyData = async (weekStart: Date) => {
    setLoadingData(true);
    try {
      const weekStartStr = format(weekStart, "yyyy-MM-dd");
      const data = await logsApi.getWeeklySummary(weekStartStr);
      setWeeklySummary(data);
    } catch (err) {
      console.error("Failed to fetch weekly data:", err);
    } finally {
      setLoadingData(false);
    }
  };

  const fetchWeeklyReport = async () => {
    setLoadingReport(true);
    try {
      const data = await adviceApi.getWeeklyReport();
      setWeeklyReport(data);
    } catch (err) {
      console.error("Failed to fetch weekly report:", err);
    } finally {
      setLoadingReport(false);
    }
  };

  useEffect(() => {
    fetchWeeklyData(currentWeek);
  }, [currentWeek]);

  // ==========================================
  // Computed stats
  // ==========================================

  const daysLogged = weeklySummary?.daily_summaries.filter(
    (d) => d.total_calories > 0
  ).length ?? 0;

  const bestDay = weeklySummary?.daily_summaries.reduce(
    (best, d) =>
      d.goal_percentage !== null &&
      (best === null || d.goal_percentage > (best.goal_percentage ?? 0))
        ? d
        : best,
    null as DailySummary | null
  );

  const streakDays = (() => {
    if (!weeklySummary) return 0;
    const summaries = [...weeklySummary.daily_summaries].reverse();
    let streak = 0;
    for (const d of summaries) {
      if (d.total_calories > 0) streak++;
      else break;
    }
    return streak;
  })();

  // ==========================================
  // Render
  // ==========================================

  return (
    <div className="min-h-screen bg-gray-50">

      {/* Header */}
      <header className="sticky top-0 z-10 bg-white border-b border-gray-100 px-4 py-3">
        <div className="max-w-lg mx-auto flex items-center gap-3">
          <button
            onClick={() => router.back()}
            className="p-1.5 rounded-xl hover:bg-gray-100 text-gray-400 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-base font-bold text-gray-800">Dashboard</h1>
            <p className="text-xs text-gray-400">Weekly nutrition overview</p>
          </div>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-5 space-y-4 pb-10">

        {/* Week selector */}
        <WeekSelector
          currentWeek={currentWeek}
          onChange={(week) => {
            setCurrentWeek(week);
            setWeeklyReport(null);
          }}
        />

        {/* Stat cards */}
        <div className="grid grid-cols-2 gap-3">
          <StatCard
            icon={<Calendar className="w-4 h-4 text-blue-600" />}
            label="Days logged"
            value={`${daysLogged} / 7`}
            sub="This week"
            color="bg-blue-50"
          />
          <StatCard
            icon={<TrendingUp className="w-4 h-4 text-primary-600" />}
            label="Avg calories"
            value={`${Math.round(weeklySummary?.avg_calories ?? 0)}`}
            sub={
              weeklySummary?.calorie_goal
                ? `Goal: ${Math.round(weeklySummary.calorie_goal)} kcal`
                : "No goal set"
            }
            color="bg-primary-50"
          />
          <StatCard
            icon={<Award className="w-4 h-4 text-yellow-600" />}
            label="Current streak"
            value={`${streakDays} day${streakDays !== 1 ? "s" : ""}`}
            sub="Keep it up!"
            color="bg-yellow-50"
          />
          <StatCard
            icon={<Target className="w-4 h-4 text-purple-600" />}
            label="Best day"
            value={
              bestDay
                ? `${Math.round(bestDay.goal_percentage ?? 0)}%`
                : "N/A"
            }
            sub={bestDay ? format(new Date(bestDay.date), "EEE, MMM d") : "No data"}
            color="bg-purple-50"
          />
        </div>

        {/* Days logged tracker */}
        {weeklySummary && (
          <DaysLoggedTracker
            dailySummaries={weeklySummary.daily_summaries}
          />
        )}

        {/* Calorie chart */}
        <div className="bg-white rounded-2xl border border-gray-100 p-4">
          <h3 className="font-semibold text-gray-700 mb-4">Nutrition Chart</h3>
          <CalorieChart
            data={weeklySummary?.daily_summaries ?? []}
            calorieGoal={weeklySummary?.calorie_goal}
            isLoading={loadingData}
          />
        </div>

        {/* Weekly averages */}
        {weeklySummary && (
          <NutritionBadge
            data={{
              calories: weeklySummary.avg_calories,
              protein: weeklySummary.avg_protein,
              carbohydrates: weeklySummary.avg_carbohydrates,
              fat: weeklySummary.avg_fat,
              fiber: null,
              sugar: null,
              sodium: null,
              calorie_goal: weeklySummary.calorie_goal,
            }}
            title="Weekly Averages"
            variant="card"
            size="md"
            showGoals
          />
        )}

        {/* AI weekly report */}
        <WeeklyReportCard
          report={weeklyReport}
          daysLogged={daysLogged}
          loading={loadingReport}
          onRefresh={fetchWeeklyReport}
        />

      </main>
    </div>
  );
}