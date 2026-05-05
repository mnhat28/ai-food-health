"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from "recharts";
import { format, parseISO } from "date-fns";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

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

interface CalorieChartProps {
  data: DailySummary[];
  calorieGoal?: number | null;
  isLoading?: boolean;
}

type ActiveTab = "calories" | "macros";

// ==========================================
// Custom tooltip
// ==========================================

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number; name: string; color: string }>;
  label?: string;
}) {
  if (!active || !payload || !payload.length) return null;

  return (
    <div className="bg-white border border-gray-100 rounded-xl shadow-lg px-4 py-3 text-sm">
      <p className="font-semibold text-gray-700 mb-2">
        {label ? format(parseISO(label), "EEE, MMM d") : ""}
      </p>
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center gap-2">
          <span
            className="w-2 h-2 rounded-full"
            style={{ background: entry.color }}
          />
          <span className="text-gray-500 capitalize">{entry.name}:</span>
          <span className="font-semibold text-gray-700">
            {Math.round(entry.value)}
            {entry.name === "calories" ? " kcal" : "g"}
          </span>
        </div>
      ))}
    </div>
  );
}

// ==========================================
// Stat card
// ==========================================

function StatCard({
  label,
  value,
  unit,
  goal,
  color,
}: {
  label: string;
  value: number;
  unit: string;
  goal?: number | null;
  color: string;
}) {
  const percentage = goal ? Math.round((value / goal) * 100) : null;

  return (
    <div className="bg-white rounded-2xl p-4 border border-gray-100">
      <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">
        {label}
      </p>
      <p className={`text-2xl font-bold mt-1 ${color}`}>
        {Math.round(value)}
        <span className="text-sm font-normal text-gray-400 ml-1">{unit}</span>
      </p>
      {percentage !== null && (
        <div className="mt-2">
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>Goal: {Math.round(goal!)} {unit}</span>
            <span>{percentage}%</span>
          </div>
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${Math.min(percentage, 100)}%`,
                background: color.includes("green")
                  ? "#16a34a"
                  : color.includes("blue")
                  ? "#2563eb"
                  : color.includes("yellow")
                  ? "#ca8a04"
                  : "#9333ea",
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

// ==========================================
// Skeleton loader
// ==========================================

function ChartSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="grid grid-cols-2 gap-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-24 bg-gray-100 rounded-2xl" />
        ))}
      </div>
      <div className="h-52 bg-gray-100 rounded-2xl" />
    </div>
  );
}

// ==========================================
// Trend indicator
// ==========================================

function TrendIndicator({ data }: { data: DailySummary[] }) {
  if (data.length < 2) return null;

  const recent = data.slice(-3);
  const avg = recent.reduce((s, d) => s + d.total_calories, 0) / recent.length;
  const prev = data.slice(-6, -3);
  const prevAvg = prev.length
    ? prev.reduce((s, d) => s + d.total_calories, 0) / prev.length
    : avg;

  const diff = avg - prevAvg;
  const pct = Math.abs(Math.round((diff / prevAvg) * 100));

  if (Math.abs(diff) < 50) {
    return (
      <span className="flex items-center gap-1 text-xs text-gray-400">
        <Minus className="w-3 h-3" />
        Stable
      </span>
    );
  }

  if (diff > 0) {
    return (
      <span className="flex items-center gap-1 text-xs text-orange-500">
        <TrendingUp className="w-3 h-3" />
        +{pct}% vs last period
      </span>
    );
  }

  return (
    <span className="flex items-center gap-1 text-xs text-green-500">
      <TrendingDown className="w-3 h-3" />
      -{pct}% vs last period
    </span>
  );
}

// ==========================================
// Main component
// ==========================================

export default function CalorieChart({
  data,
  calorieGoal,
  isLoading = false,
}: CalorieChartProps) {
  const [activeTab, setActiveTab] = useState<ActiveTab>("calories");

  if (isLoading) return <ChartSkeleton />;

  if (!data || data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="w-14 h-14 rounded-full bg-gray.100 flex items-center justify-center mb-3">
          <span className="text-2xl">📊</span>
        </div>
        <p className="font-semibold text-gray-600">No data yet</p>
        <p className="text-sm text-gray-400 mt-1">
          Start logging meals to see your nutrition chart
        </p>
      </div>
    );
  }

  const avgCalories = Math.round(
    data.reduce((s, d) => s + d.total_calories, 0) / data.length
  );
  const avgProtein = Math.round(
    data.reduce((s, d) => s + d.total_protein, 0) / data.length
  );
  const avgCarbs = Math.round(
    data.reduce((s, d) => s + d.total_carbohydrates, 0) / data.length
  );
  const avgFat = Math.round(
    data.reduce((s, d) => s + d.total_fat, 0) / data.length
  );

  const chartData = data.map((d) => ({
    ...d,
    date: d.date,
    label: format(parseISO(d.date), "EEE"),
  }));

  return (
    <div className="space-y-4">

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard
          label="Avg Calories"
          value={avgCalories}
          unit="kcal"
          goal={calorieGoal}
          color="text-primary-600"
        />
        <StatCard
          label="Avg Protein"
          value={avgProtein}
          unit="g"
          color="text-green-600"
        />
        <StatCard
          label="Avg Carbs"
          value={avgCarbs}
          unit="g"
          color="text-blue-600"
        />
        <StatCard
          label="Avg Fat"
          value={avgFat}
          unit="g"
          color="text-yellow-600"
        />
      </div>

      {/* Chart card */}
      <div className="bg-white rounded-2xl border border-gray-100 p-4">

        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-semibold text-gray-700">Weekly Overview</h3>
            <TrendIndicator data={data} />
          </div>

          {/* Tab switcher */}
          <div className="flex bg-gray-100 rounded-lg p-0.5">
            {(["calories", "macros"] as ActiveTab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`
                  px-3 py-1.5 rounded-md text-xs font-medium capitalize transition-all
                  ${activeTab === tab
                    ? "bg-white text-gray-700 shadow-sm"
                    : "text-gray-400 hover:text-gray-600"
                  }
                `}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Calories chart */}
        {activeTab === "calories" && (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} barSize={28}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 12, fill: "#94a3b8" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "#94a3b8" }}
                axisLine={false}
                tickLine={false}
                width={36}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: "#f8fafc" }} />
              {calorieGoal && (
                <ReferenceLine
                  y={calorieGoal}
                  stroke="#16a34a"
                  strokeDasharray="4 4"
                  label={{
                    value: "Goal",
                    position: "right",
                    fontSize: 11,
                    fill: "#16a34a",
                  }}
                />
              )}
              <Bar dataKey="total_calories" name="calories" radius={[6, 6, 0, 0]}>
                {chartData.map((entry, index) => {
                  const pct = calorieGoal
                    ? entry.total_calories / calorieGoal
                    : 1;
                  const color =
                    pct >= 0.9
                      ? "#16a34a"
                      : pct >= 0.5
                      ? "#eab308"
                      : "#e2e8f0";
                  return <Cell key={index} fill={color} />;
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}

        {/* Macros chart */}
        {activeTab === "macros" && (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} barSize={8}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 12, fill: "#94a3b8" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "#94a3b8" }}
                axisLine={false}
                tickLine={false}
                width={36}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: "#f8fafc" }} />
              <Bar
                dataKey="total_protein"
                name="protein"
                fill="#16a34a"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                dataKey="total_carbohydrates"
                name="carbs"
                fill="#2563eb"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                dataKey="total_fat"
                name="fat"
                fill="#eab308"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        )}

        {/* Legend for macros */}
        {activeTab === "macros" && (
          <div className="flex items-center justify-center gap-4 mt-3">
            {[
              { color: "#16a34a", label: "Protein" },
              { color: "#2563eb", label: "Carbs" },
              { color: "#eab308", label: "Fat" },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-1.5">
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ background: item.color }}
                />
                <span className="text-xs text-gray-400">{item.label}</span>
              </div>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}