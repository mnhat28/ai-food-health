"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import { adviceApi, logsApi } from "@/lib/api";
import { format } from "date-fns";
import { Toaster } from "react-hot-toast";
import {
  Flame,
  History,
  Lightbulb,
  User,
  Plus,
  X,
  BarChart2,
} from "lucide-react";

import FoodUploader from "@/components/FoodUploader";
import NutritionBadge from "@/components/NutritionBadge";
import FoodLogCard from "@/components/FoodLogCard";

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
  meals: Record<string, Array<{ food_name: string; calories: number }>>
}

interface FoodLog {
  id: string;
  food_name: string;
  food_name_en: string | null;
  image_url: string | null;
  confidence: number | null;
  calories: number;
  protein: number | null;
  carbohydrates: number | null;
  fat: number | null;
  fiber: number | null;
  serving_size: number;
  serving_unit: string;
  meal_type: string;
  eaten_at: string;
  note: string | null;
  total_calories: number;
  total_protein: number | null;
  total_carbohydrates: number | null;
  total_fat: number | null;
}

// ==========================================
// Bottom nav item
// ==========================================

function NavItem({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        flex flex-col items-center gap-1 px-4 py-2 rounded-xl transition-all
        ${active
          ? "text-primary-600"
          : "text-gray-400 hover:text-gray-600"
        }
      `}
    >
      {icon}
      <span className="text-xs font-medium">{label}</span>
    </button>
  );
}

// ==========================================
// Daily tip banner
// ==========================================

function DailyTipBanner({ tip }: { tip: string }) {
  const [visible, setVisible] = useState(true);
  if (!visible) return null;

  return (
    <div className="relative bg-gradient-to-r from-primary-50 to-emerald-50 border border-primary-100 rounded-2xl px-4 py-3 animate-fade-in">
      <button
        onClick={() => setVisible(false)}
        className="absolute top-2 right-2 p-1 rounded-full hover:bg-primary-100 text-primary-400 transition-colors"
      >
        <X className="w-3.5 h-3.5" />
      </button>
      <div className="flex gap-3 pr-4">
        <span className="text-xl shrink-0">💡</span>
        <div>
          <p className="text-xs font-semibold text-primary-700 uppercase tracking-wide mb-0.5">
            Daily Tip
          </p>
          <p className="text-sm text-gray-600 leading-relaxed">{tip}</p>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// Meal group
// ==========================================

function MealGroup({
  mealType,
  logs,
  onDeleted,
  onUpdated,
}: {
  mealType: string;
  logs: FoodLog[];
  onDeleted: () => void;
  onUpdated: () => void;
}) {
  const MEAL_EMOJI: Record<string, string> = {
    breakfast: "🌅",
    lunch: "☀️",
    dinner: "🌙",
    snack: "🍎",
  };

  const totalCal = Math.round(
    logs.reduce((s, l) => s + l.total_calories, 0)
  );

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between px-1">
        <span className="text-sm font-semibold text-gray-600 capitalize">
          {MEAL_EMOJI[mealType]} {mealType}
        </span>
        <span className="text-xs text-gray-400">{totalCal} kcal</span>
      </div>
      {logs.map((log) => (
        <FoodLogCard
          key={log.id}
          log={log}
          onDeleted={onDeleted}
          onUpdated={onUpdated}
        />
      ))}
    </div>
  );
}

// ==========================================
// Tab views
// ==========================================

function HomeTab({
  summary,
  logs,
  dailyTip,
  onLogCreated,
  onLogDeleted,
  onLogUpdated,
  showUploader,
  setShowUploader,
}: {
  summary: DailySummary | null;
  logs: FoodLog[];
  dailyTip: string | null;
  onLogCreated: () => void;
  onLogDeleted: () => void;
  onLogUpdated: () => void;
  showUploader: boolean;
  setShowUploader: (v: boolean) => void;
}) {
  const mealOrder = ["breakfast", "lunch", "dinner", "snack"];
  const grouped = mealOrder.reduce((acc, meal) => {
    const filtered = logs.filter((l) => l.meal_type === meal);
    if (filtered.length > 0) acc[meal] = filtered;
    return acc;
  }, {} as Record<string, FoodLog[]>);

  return (
    <div className="space-y-5">

      {/* Daily tip */}
      {dailyTip && <DailyTipBanner tip={dailyTip} />}

      {/* Nutrition summary */}
      {summary && (
        <NutritionBadge
          data={{
            calories: summary.total_calories,
            protein: summary.total_protein,
            carbohydrates: summary.total_carbohydrates,
            fat: summary.total_fat,
            fiber: null,
            sugar: null,
            sodium: null,
            calorie_goal: summary.calorie_goal,
          }}
          title={`Today — ${format(new Date(), "MMMM d")}`}
          variant="card"
          size="md"
          showGoals
        />
      )}

      {/* Upload section */}
      {showUploader ? (
        <div className="bg-white rounded-2xl border border-gray-100 p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-700">Log a meal</h3>
            <button
              onClick={() => setShowUploader(false)}
              className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <FoodUploader
            onLogCreated={() => {
              setShowUploader(false);
              onLogCreated();
            }}
          />
        </div>
      ) : (
        <button
          onClick={() => setShowUploader(true)}
          className="w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl border-2 border-dashed border-primary-200 text-primary-600 font-medium text-sm hover:border-primary-400 hover:bg-primary-50 transition-all"
        >
          <Plus className="w-4 h-4" />
          Log a meal
        </button>
      )}

      {/* Food logs grouped by meal */}
      {Object.keys(grouped).length > 0 ? (
        <div className="space-y-5">
          {mealOrder
            .filter((m) => grouped[m])
            .map((meal) => (
              <MealGroup
                key={meal}
                mealType={meal}
                logs={grouped[meal]}
                onDeleted={onLogDeleted}
                onUpdated={onLogUpdated}
              />
            ))}
        </div>
      ) : (
        !showUploader && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <span className="text-4xl mb-3">🍽️</span>
            <p className="font-semibold text-gray-600">No meals logged yet</p>
            <p className="text-sm text-gray-400 mt-1">
              Tap the button above to log your first meal
            </p>
          </div>
        )
      )}

    </div>
  );
}

// ==========================================
// Main page
// ==========================================

export default function HomePage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"home" | "history" | "advice" | "profile">("home");
  const [showUploader, setShowUploader] = useState(false);
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [logs, setLogs] = useState<FoodLog[]>([]);
  const [dailyTip, setDailyTip] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // ==========================================
  // Auth guard
  // ==========================================

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/auth/login");
    }
  }, [router]);

  // ==========================================
  // Data fetching
  // ==========================================

  const fetchTodayData = async () => {
    try {
      const today = format(new Date(), "yyyy-MM-dd");
      const [summaryData, logsData] = await Promise.all([
        logsApi.getDailySummary(today),
        logsApi.getLogs({ date: today, limit: 50 }),
      ]);
      setSummary(summaryData);
      setLogs(logsData);
    } catch (err) {
      console.error("Failed to fetch today data:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchDailyTip = async () => {
    try {
      const data = await adviceApi.getDailyTip();
      setDailyTip(data.tip);
    } catch {
      // Silent fail — tip is non-critical
    }
  };

  useEffect(() => {
    fetchTodayData();
    fetchDailyTip();
  }, []);

  // ==========================================
  // Render
  // ==========================================

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-gray-400">Loading your data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Toaster position="top-center" />

      {/* Header */}
      <header className="sticky top-0 z-10 bg-white border-b border-gray-100 px-4 py-3">
        <div className="max-w-lg mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-800">
              🥗 AI Food Health
            </h1>
            <p className="text-xs text-gray-400">
              {format(new Date(), "EEEE, MMMM d")}
            </p>
          </div>
          <button
            onClick={() => router.push("/dashboard")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-primary-50 text-primary-600 text-xs font-medium hover:bg-primary-100 transition-colors"
          >
            <BarChart2 className="w-3.5 h-3.5" />
            Dashboard
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-lg mx-auto px-4 py-5 pb-24">
        {activeTab === "home" && (
          <HomeTab
            summary={summary}
            logs={logs}
            dailyTip={dailyTip}
            onLogCreated={fetchTodayData}
            onLogDeleted={fetchTodayData}
            onLogUpdated={fetchTodayData}
            showUploader={showUploader}
            setShowUploader={setShowUploader}
          />
        )}

        {activeTab === "history" && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <span className="text-4xl mb-3">📅</span>
            <p className="font-semibold text-gray-600">Food History</p>
            <p className="text-sm text-gray-400 mt-1">
              Coming soon — go to{" "}
              <button
                onClick={() => router.push("/history")}
                className="text-primary-600 underline"
              >
                full history page
              </button>
            </p>
          </div>
        )}

        {activeTab === "advice" && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <span className="text-4xl mb-3">🤖</span>
            <p className="font-semibold text-gray-600">AI Nutrition Advice</p>
            <p className="text-sm text-gray-400 mt-1">
              Go to the{" "}
              <button
                onClick={() => router.push("/advice")}
                className="text-primary-600 underline"
              >
                advice page
              </button>{" "}
              for full experience
            </p>
          </div>
        )}

        {activeTab === "profile" && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <span className="text-4xl mb-3">👤</span>
            <p className="font-semibold text-gray-600">Profile</p>
            <button
              onClick={() => router.push("/auth/profile")}
              className="mt-3 px-4 py-2 rounded-xl bg-primary-600 text-white text-sm font-medium"
            >
              View Profile
            </button>
          </div>
        )}
      </main>

      {/* Bottom navigation */}
      <nav className="fixed bottom-0 left-0 right-0 z-10 bg-white border-t border-gray-100 px-4 py-2">
        <div className="max-w-lg mx-auto flex items-center justify-around">
          <NavItem
            icon={<Flame className="w-5 h-5" />}
            label="Today"
            active={activeTab === "home"}
            onClick={() => setActiveTab("home")}
          />
          <NavItem
            icon={<History className="w-5 h-5" />}
            label="History"
            active={activeTab === "history"}
            onClick={() => setActiveTab("history")}
          />
          <NavItem
            icon={<Lightbulb className="w-5 h-5" />}
            label="Advice"
            active={activeTab === "advice"}
            onClick={() => setActiveTab("advice")}
          />
          <NavItem
            icon={<User className="w-5 h-5" />}
            label="Profile"
            active={activeTab === "profile"}
            onClick={() => setActiveTab("profile")}
          />
        </div>
      </nav>

    </div>
  );
}