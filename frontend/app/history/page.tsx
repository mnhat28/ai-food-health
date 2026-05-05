"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { logsApi } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import {
  format,
  parseISO,
  startOfMonth,
  endOfMonth,
  eachDayOfInterval,
  isSameDay,
  isToday,
  subMonths,
  addMonths,
} from "date-fns";
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Filter,
  Search,
  X,
  Flame,
} from "lucide-react";
import FoodLogCard from "@/components/FoodLogCard";

// ==========================================
// Types
// ==========================================

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

interface DailySummary {
  date: string;
  total_calories: number;
  total_protein: number;
  total_carbohydrates: number;
  total_fat: number;
  calorie_goal: number | null;
  goal_percentage: number | null;
}

type MealFilter = "all" | "breakfast" | "lunch" | "dinner" | "snack";

// ==========================================
// Mini calendar
// ==========================================

function MiniCalendar({
  currentMonth,
  selectedDate,
  activeDates,
  onSelectDate,
  onChangeMonth,
}: {
  currentMonth: Date;
  selectedDate: Date | null;
  activeDates: string[];
  onSelectDate: (date: Date) => void;
  onChangeMonth: (month: Date) => void;
}) {
  const days = eachDayOfInterval({
    start: startOfMonth(currentMonth),
    end: endOfMonth(currentMonth),
  });

  const firstDayOfWeek = startOfMonth(currentMonth).getDay();
  const blanks = Array(firstDayOfWeek).fill(null);

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-4">

      {/* Month navigation */}
      <div className="flex items-center justify-between mb-3">
        <button
          onClick={() => onChangeMonth(subMonths(currentMonth, 1))}
          className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <p className="text-sm font-semibold text-gray-700">
          {format(currentMonth, "MMMM yyyy")}
        </p>
        <button
          onClick={() => onChangeMonth(addMonths(currentMonth, 1))}
          disabled={addMonths(currentMonth, 1) > new Date()}
          className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors disabled:opacity-30"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Day headers */}
      <div className="grid grid-cols-7 mb-1">
        {["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map((d) => (
          <div key={d} className="text-center text-xs text-gray-400 font-medium py-1">
            {d}
          </div>
        ))}
      </div>

      {/* Day cells */}
      <div className="grid grid-cols-7 gap-y-1">
        {blanks.map((_, i) => (
          <div key={`blank-${i}`} />
        ))}
        {days.map((day) => {
          const dateStr = format(day, "yyyy-MM-dd");
          const hasData = activeDates.includes(dateStr);
          const isSelected = selectedDate && isSameDay(day, selectedDate);
          const isTodayDate = isToday(day);
          const isFuture = day > new Date();

          return (
            <button
              key={dateStr}
              onClick={() => !isFuture && onSelectDate(day)}
              disabled={isFuture}
              className={`
                relative flex flex-col items-center justify-center
                h-9 w-full rounded-xl text-xs font-medium transition-all
                ${isFuture ? "opacity-30 cursor-not-allowed" : "cursor-pointer"}
                ${isSelected
                  ? "bg-primary-600 text-white"
                  : isTodayDate
                  ? "bg-primary-50 text-primary-600"
                  : "hover:bg-gray-100 text-gray-700"
                }
              `}
            >
              {day.getDate()}
              {/* Dot indicator for days with logs */}
              {hasData && !isSelected && (
                <span className="absolute bottom-1 w-1 h-1 rounded-full bg-primary-400" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ==========================================
// Filter bar
// ==========================================

function FilterBar({
  mealFilter,
  onMealFilterChange,
  searchQuery,
  onSearchChange,
}: {
  mealFilter: MealFilter;
  onMealFilterChange: (f: MealFilter) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
}) {
  const filters: { value: MealFilter; label: string; emoji: string }[] = [
    { value: "all", label: "All", emoji: "🍽️" },
    { value: "breakfast", label: "Breakfast", emoji: "🌅" },
    { value: "lunch", label: "Lunch", emoji: "☀️" },
    { value: "dinner", label: "Dinner", emoji: "🌙" },
    { value: "snack", label: "Snack", emoji: "🍎" },
  ];

  return (
    <div className="space-y-3">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search food logs..."
          className="w-full pl-9 pr-9 py-2.5 text-sm bg-white border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-300 text-gray-700 placeholder:text-gray-400"
        />
        {searchQuery && (
          <button
            onClick={() => onSearchChange("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 rounded-full hover:bg-gray-100 text-gray-400"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Meal type filter */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        {filters.map((f) => (
          <button
            key={f.value}
            onClick={() => onMealFilterChange(f.value)}
            className={`
              flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium
              whitespace-nowrap transition-all shrink-0
              ${mealFilter === f.value
                ? "bg-primary-600 text-white"
                : "bg-white border border-gray-200 text-gray-500 hover:border-primary-300"
              }
            `}
          >
            <span>{f.emoji}</span>
            {f.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ==========================================
// Day summary header
// ==========================================

function DaySummaryHeader({ summary }: { summary: DailySummary | null }) {
  if (!summary || summary.total_calories === 0) return null;

  return (
    <div className="flex items-center gap-4 bg-white rounded-2xl border border-gray-100 px-4 py-3">
      <div className="flex items-center gap-2">
        <Flame className="w-4 h-4 text-primary-500" />
        <span className="text-sm font-bold text-primary-600">
          {Math.round(summary.total_calories)} kcal
        </span>
      </div>
      <div className="w-px h-4 bg-gray-200" />
      {summary.total_protein > 0 && (
        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-400">P</span>
          <span className="text-xs font-semibold text-green-600">
            {Math.round(summary.total_protein)}g
          </span>
        </div>
      )}
      {summary.total_carbohydrates > 0 && (
        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-400">C</span>
          <span className="text-xs font-semibold text-blue-600">
            {Math.round(summary.total_carbohydrates)}g
          </span>
        </div>
      )}
      {summary.total_fat > 0 && (
        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-400">F</span>
          <span className="text-xs font-semibold text-yellow-600">
            {Math.round(summary.total_fat)}g
          </span>
        </div>
      )}
      {summary.goal_percentage !== null && (
        <>
          <div className="w-px h-4 bg-gray-200" />
          <span className={`text-xs font-medium ${
            summary.goal_percentage >= 90
              ? "text-green-600"
              : summary.goal_percentage >= 50
              ? "text-yellow-600"
              : "text-gray-400"
          }`}>
            {Math.round(summary.goal_percentage)}% of goal
          </span>
        </>
      )}
    </div>
  );
}

// ==========================================
// Main page
// ==========================================

export default function HistoryPage() {
  const router = useRouter();
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [logs, setLogs] = useState<FoodLog[]>([]);
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [activeDates, setActiveDates] = useState<string[]>([]);
  const [mealFilter, setMealFilter] = useState<MealFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [showCalendar, setShowCalendar] = useState(true);

  // ==========================================
  // Auth guard
  // ==========================================

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/auth/login");
    }
  }, [router]);

  // ==========================================
  // Fetch logs for selected date
  // ==========================================

  const fetchLogsForDate = useCallback(async (date: Date) => {
    setLoading(true);
    try {
      const dateStr = format(date, "yyyy-MM-dd");
      const [logsData, summaryData] = await Promise.all([
        logsApi.getLogs({ date: dateStr, limit: 50 }),
        logsApi.getDailySummary(dateStr),
      ]);
      setLogs(logsData);
      setSummary(summaryData);
    } catch (err) {
      console.error("Failed to fetch logs:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  // ==========================================
  // Fetch active dates for current month
  // ==========================================

  const fetchActiveDates = useCallback(async (month: Date) => {
    try {
      const start = format(startOfMonth(month), "yyyy-MM-dd");
      const end = format(endOfMonth(month), "yyyy-MM-dd");
      const allLogs = await logsApi.getLogs({
        limit: 100,
      });

      const dates = allLogs
        .filter((log: FoodLog) => {
          const logDate = format(parseISO(log.eaten_at), "yyyy-MM-dd");
          return logDate >= start && logDate <= end;
        })
        .map((log: FoodLog) => format(parseISO(log.eaten_at), "yyyy-MM-dd"));

      setActiveDates([...new Set<string>(dates)]);
    } catch {
      // Silent fail
    }
  }, []);

  useEffect(() => {
    fetchLogsForDate(selectedDate);
  }, [selectedDate, fetchLogsForDate]);

  useEffect(() => {
    fetchActiveDates(currentMonth);
  }, [currentMonth, fetchActiveDates]);

  // ==========================================
  // Filtered logs
  // ==========================================

  const filteredLogs = logs.filter((log) => {
    const matchesMeal = mealFilter === "all" || log.meal_type === mealFilter;
    const matchesSearch = !searchQuery ||
      log.food_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (log.food_name_en?.toLowerCase().includes(searchQuery.toLowerCase()) ?? false);
    return matchesMeal && matchesSearch;
  });

  const groupedLogs = filteredLogs.reduce((acc, log) => {
    const meal = log.meal_type;
    if (!acc[meal]) acc[meal] = [];
    acc[meal].push(log);
    return acc;
  }, {} as Record<string, FoodLog[]>);

  const mealOrder = ["breakfast", "lunch", "dinner", "snack"];

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
          <div className="flex-1">
            <h1 className="text-base font-bold text-gray-800">Food History</h1>
            <p className="text-xs text-gray-400">
              {format(selectedDate, "EEEE, MMMM d, yyyy")}
            </p>
          </div>
          <button
            onClick={() => setShowCalendar(!showCalendar)}
            className={`
              p-1.5 rounded-xl transition-colors
              ${showCalendar
                ? "bg-primary-50 text-primary-600"
                : "hover:bg-gray-100 text-gray-400"
              }
            `}
          >
            <Filter className="w-4 h-4" />
          </button>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-4 space-y-4 pb-10">

        {/* Mini calendar */}
        {showCalendar && (
          <MiniCalendar
            currentMonth={currentMonth}
            selectedDate={selectedDate}
            activeDates={activeDates}
            onSelectDate={setSelectedDate}
            onChangeMonth={setCurrentMonth}
          />
        )}

        {/* Filter bar */}
        <FilterBar
          mealFilter={mealFilter}
          onMealFilterChange={setMealFilter}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
        />

        {/* Day summary */}
        <DaySummaryHeader summary={summary} />

        {/* Logs */}
        {loading ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className="h-20 bg-white rounded-2xl border border-gray-100 animate-pulse"
              />
            ))}
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-14 text-center">
            <span className="text-4xl mb-3">
              {searchQuery ? "🔍" : "📭"}
            </span>
            <p className="font-semibold text-gray-600">
              {searchQuery
                ? `No results for "${searchQuery}"`
                : "No meals logged"
              }
            </p>
            <p className="text-sm text-gray-400 mt-1">
              {searchQuery
                ? "Try a different search term"
                : `Nothing logged on ${format(selectedDate, "MMMM d")}`
              }
            </p>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="mt-3 text-sm text-primary-600 font-medium"
              >
                Clear search
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-5">
            {mealOrder
              .filter((meal) => groupedLogs[meal])
              .map((meal) => (
                <div key={meal} className="space-y-2">
                  <div className="flex items-center justify-between px-1">
                    <span className="text-sm font-semibold text-gray-600 capitalize">
                      {{
                        breakfast: "🌅",
                        lunch: "☀️",
                        dinner: "🌙",
                        snack: "🍎",
                      }[meal]} {meal}
                    </span>
                    <span className="text-xs text-gray-400">
                      {Math.round(
                        groupedLogs[meal].reduce(
                          (s, l) => s + l.total_calories, 0
                        )
                      )} kcal
                    </span>
                  </div>
                  {groupedLogs[meal].map((log) => (
                    <FoodLogCard
                      key={log.id}
                      log={log}
                      onDeleted={() => fetchLogsForDate(selectedDate)}
                      onUpdated={() => fetchLogsForDate(selectedDate)}
                    />
                  ))}
                </div>
              ))}
          </div>
        )}

      </main>
    </div>
  );
}