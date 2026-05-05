"use client";

import { useState } from "react";
import {
  Flame,
  Beef,
  Wheat,
  Droplets,
  Leaf,
  ChevronDown,
  ChevronUp,
  Info,
} from "lucide-react";

// ==========================================
// Types
// ==========================================

interface NutritionData {
  calories: number;
  protein: number | null;
  carbohydrates: number | null;
  fat: number | null;
  fiber: number | null;
  sugar: number | null;
  sodium: number | null;
  calorie_goal?: number | null;
  protein_goal?: number | null;
  carb_goal?: number | null;
  fat_goal?: number | null;
}

interface NutritionBadgeProps {
  data: NutritionData;
  title?: string;
  showGoals?: boolean;
  showDetails?: boolean;
  size?: "sm" | "md" | "lg";
  variant?: "card" | "inline" | "compact";
}

// ==========================================
// Constants
// ==========================================

const SIZE_CONFIG = {
  sm: {
    calories: "text-2xl",
    label: "text-xs",
    macro: "text-sm",
    padding: "p-3",
    gap: "gap-2",
  },
  md: {
    calories: "text-3xl",
    label: "text-xs",
    macro: "text-base",
    padding: "p-4",
    gap: "gap-3",
  },
  lg: {
    calories: "text-4xl",
    label: "text-sm",
    macro: "text-lg",
    padding: "p-6",
    gap: "gap-4",
  },
};

// ==========================================
// Progress ring (SVG)
// ==========================================

function ProgressRing({
  value,
  goal,
  color,
  size = 56,
}: {
  value: number;
  goal: number;
  color: string;
  size?: number;
}) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.min(value / goal, 1);
  const offset = circumference - pct * circumference;

  return (
    <svg width={size} height={size} className="-rotate-90">
      {/* Background ring */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="#f1f5f9"
        strokeWidth={4}
      />
      {/* Progress ring */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={4}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="transition-all duration-700"
      />
    </svg>
  );
}

// ==========================================
// Macro row
// ==========================================

function MacroRow({
  icon,
  label,
  value,
  unit,
  goal,
  color,
  barColor,
}: {
  icon: React.ReactNode;
  label: string;
  value: number | null;
  unit: string;
  goal?: number | null;
  color: string;
  barColor: string;
}) {
  if (value === null) return null;

  const pct = goal ? Math.min(Math.round((value / goal) * 100), 100) : null;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={color}>{icon}</span>
          <span className="text-sm text-gray-600">{label}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-semibold text-gray-700">
            {Math.round(value)}{unit}
          </span>
          {goal && (
            <span className="text-xs text-gray-400">
              / {Math.round(goal)}{unit}
            </span>
          )}
          {pct !== null && (
            <span
              className={`
                text-xs font-medium px-1.5 py-0.5 rounded-md
                ${pct >= 90
                  ? "bg-green-50 text-green-600"
                  : pct >= 50
                  ? "bg-yellow-50 text-yellow-600"
                  : "bg-gray-50 text-gray-400"
                }
              `}
            >
              {pct}%
            </span>
          )}
        </div>
      </div>

      {/* Progress bar */}
      {goal && (
        <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full ${barColor} transition-all duration-500`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  );
}

// ==========================================
// Calorie donut
// ==========================================

function CalorieDonut({
  calories,
  goal,
  size,
}: {
  calories: number;
  goal: number | null | undefined;
  size: "sm" | "md" | "lg";
}) {
  const ringSize = size === "lg" ? 96 : size === "md" ? 80 : 64;
  const pct = goal ? Math.min(Math.round((calories / goal) * 100), 100) : null;
  const color =
    pct === null
      ? "#16a34a"
      : pct >= 90
      ? "#16a34a"
      : pct >= 50
      ? "#eab308"
      : "#e2e8f0";

  return (
    <div className="relative flex items-center justify-center">
      {goal ? (
        <>
          <ProgressRing value={calories} goal={goal} color={color} size={ringSize} />
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`font-bold text-gray-800 ${SIZE_CONFIG[size].calories}`}>
              {Math.round(calories)}
            </span>
            <span className="text-xs text-gray-400">kcal</span>
          </div>
        </>
      ) : (
        <div className="flex flex-col items-center">
          <span className={`font-bold text-primary-600 ${SIZE_CONFIG[size].calories}`}>
            {Math.round(calories)}
          </span>
          <span className="text-xs text-gray-400">kcal</span>
        </div>
      )}
    </div>
  );
}

// ==========================================
// Compact variant
// ==========================================

function CompactBadge({ data }: { data: NutritionData }) {
  return (
    <div className="flex items-center gap-3 bg-white border border-gray-100 rounded-xl px-4 py-2.5">
      <div className="flex items-center gap-1.5">
        <Flame className="w-4 h-4 text-primary-500" />
        <span className="font-semibold text-gray-700">
          {Math.round(data.calories)}
        </span>
        <span className="text-xs text-gray-400">kcal</span>
      </div>

      <div className="w-px h-4 bg-gray-200" />

      {data.protein !== null && (
        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-400">P</span>
          <span className="text-xs font-medium text-green-600">
            {Math.round(data.protein)}g
          </span>
        </div>
      )}
      {data.carbohydrates !== null && (
        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-400">C</span>
          <span className="text-xs font-medium text-blue-600">
            {Math.round(data.carbohydrates)}g
          </span>
        </div>
      )}
      {data.fat !== null && (
        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-400">F</span>
          <span className="text-xs font-medium text-yellow-600">
            {Math.round(data.fat)}g
          </span>
        </div>
      )}
    </div>
  );
}

// ==========================================
// Inline variant
// ==========================================

function InlineBadge({ data, size }: { data: NutritionData; size: "sm" | "md" | "lg" }) {
  const cfg = SIZE_CONFIG[size];
  return (
    <div className={`flex items-center ${cfg.gap} flex-wrap`}>
      <div className="flex items-center gap-1.5">
        <Flame className="w-4 h-4 text-primary-500" />
        <span className={`font-bold text-primary-600 ${cfg.macro}`}>
          {Math.round(data.calories)}
        </span>
        <span className="text-xs text-gray-400">kcal</span>
      </div>

      {[
        { label: "P", value: data.protein, color: "text-green-600" },
        { label: "C", value: data.carbohydrates, color: "text-blue-600" },
        { label: "F", value: data.fat, color: "text-yellow-600" },
      ].map(({ label, value, color }) =>
        value !== null ? (
          <div key={label} className="flex items-center gap-1">
            <span className="text-xs text-gray-400 font-medium">{label}</span>
            <span className={`text-xs font-semibold ${color}`}>
              {Math.round(value)}g
            </span>
          </div>
        ) : null
      )}
    </div>
  );
}

// ==========================================
// Card variant (main)
// ==========================================

function CardBadge({
  data,
  title,
  showGoals,
  showDetails,
  size,
}: {
  data: NutritionData;
  title?: string;
  showGoals: boolean;
  showDetails: boolean;
  size: "sm" | "md" | "lg";
}) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const cfg = SIZE_CONFIG[size];

  const calorieGoal = showGoals ? data.calorie_goal : null;
  const proteinGoal = showGoals ? data.protein_goal : null;
  const carbGoal = showGoals ? data.carb_goal : null;
  const fatGoal = showGoals ? data.fat_goal : null;

  const calorieColor =
    calorieGoal && data.calories / calorieGoal >= 0.9
      ? "text-green-600"
      : calorieGoal && data.calories / calorieGoal >= 0.5
      ? "text-yellow-600"
      : "text-primary-600";

  return (
    <div className={`bg-white rounded-2xl border border-gray-100 ${cfg.padding}`}>

      {/* Header */}
      {title && (
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-700">{title}</h3>
          {calorieGoal && (
            <span className="flex items-center gap-1 text-xs text-gray-400">
              <Info className="w-3 h-3" />
              Goal: {Math.round(calorieGoal)} kcal
            </span>
          )}
        </div>
      )}

      {/* Calorie donut + macros side by side */}
      <div className="flex items-center gap-6">

        {/* Donut */}
        <CalorieDonut calories={data.calories} goal={calorieGoal} size={size} />

        {/* Macro bars */}
        <div className="flex-1 space-y-2.5">
          <MacroRow
            icon={<Beef className="w-3.5 h-3.5" />}
            label="Protein"
            value={data.protein}
            unit="g"
            goal={proteinGoal}
            color="text-green-500"
            barColor="bg-green-400"
          />
          <MacroRow
            icon={<Wheat className="w-3.5 h-3.5" />}
            label="Carbs"
            value={data.carbohydrates}
            unit="g"
            goal={carbGoal}
            color="text-blue-500"
            barColor="bg-blue-400"
          />
          <MacroRow
            icon={<Droplets className="w-3.5 h-3.5" />}
            label="Fat"
            value={data.fat}
            unit="g"
            goal={fatGoal}
            color="text-yellow-500"
            barColor="bg-yellow-400"
          />
        </div>
      </div>

      {/* Toggle details */}
      {showDetails && (data.fiber !== null || data.sugar !== null || data.sodium !== null) && (
        <div className="mt-4">
          <button
            onClick={() => setDetailsOpen(!detailsOpen)}
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors"
          >
            {detailsOpen
              ? <ChevronUp className="w-3.5 h-3.5" />
              : <ChevronDown className="w-3.5 h-3.5" />
            }
            {detailsOpen ? "Hide details" : "Show more details"}
          </button>

          {detailsOpen && (
            <div className="mt-3 pt-3 border-t border-gray-100 space-y-2.5 animate-fade-in">
              <MacroRow
                icon={<Leaf className="w-3.5 h-3.5" />}
                label="Fiber"
                value={data.fiber}
                unit="g"
                color="text-emerald-500"
                barColor="bg-emerald-400"
              />
              <MacroRow
                icon={<span className="text-pink-500 text-xs font-bold">S</span>}
                label="Sugar"
                value={data.sugar}
                unit="g"
                color="text-pink-500"
                barColor="bg-pink-400"
              />
              <MacroRow
                icon={<span className="text-gray-400 text-xs font-bold">Na</span>}
                label="Sodium"
                value={data.sodium}
                unit="mg"
                color="text-gray-400"
                barColor="bg-gray-300"
              />
            </div>
          )}
        </div>
      )}

    </div>
  );
}

// ==========================================
// Main component
// ==========================================

export default function NutritionBadge({
  data,
  title,
  showGoals = false,
  showDetails = false,
  size = "md",
  variant = "card",
}: NutritionBadgeProps) {
  if (variant === "compact") return <CompactBadge data={data} />;
  if (variant === "inline") return <InlineBadge data={data} size={size} />;
  return (
    <CardBadge
      data={data}
      title={title}
      showGoals={showGoals}
      showDetails={showDetails}
      size={size}
    />
  );
}