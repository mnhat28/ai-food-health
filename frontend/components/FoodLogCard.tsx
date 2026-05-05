"use client";

import { useState } from "react";
import { logsApi } from "@/lib/api";
import {
  Trash2,
  ChevronDown,
  ChevronUp,
  Clock,
  Utensils,
  Edit2,
  Check,
  X,
} from "lucide-react";
import { format, parseISO } from "date-fns";
import Image from "next/image";
import toast from "react-hot-toast";

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

interface FoodLogCardProps {
  log: FoodLog;
  onDeleted?: () => void;
  onUpdated?: () => void;
}

// ==========================================
// Constants
// ==========================================

const MEAL_EMOJI: Record<string, string> = {
  breakfast: "🌅",
  lunch: "☀️",
  dinner: "🌙",
  snack: "🍎",
};

const MEAL_COLORS: Record<string, string> = {
  breakfast: "bg-orange-50 text-orange-600 border-orange-100",
  lunch: "bg-yellow-50 text-yellow-600 border-yellow-100",
  dinner: "bg-blue-50 text-blue-600 border-blue-100",
  snack: "bg-green-50 text-green-600 border-green-100",
};

// ==========================================
// Macro pill
// ==========================================

function MacroPill({
  label,
  value,
  color,
}: {
  label: string;
  value: number | null;
  color: string;
}) {
  if (value === null) return null;
  return (
    <div className={`flex flex-col items-center px-3 py-1.5 rounded-lg ${color}`}>
      <span className="text-sm font-semibold">{Math.round(value)}g</span>
      <span className="text-xs opacity-70">{label}</span>
    </div>
  );
}

// ==========================================
// Confidence bar
// ==========================================

function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color =
    pct >= 80 ? "bg-green-400" : pct >= 60 ? "bg-yellow-400" : "bg-red-400";

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-gray-400 w-8">{pct}%</span>
    </div>
  );
}

// ==========================================
// Edit form
// ==========================================

function EditForm({
  log,
  onSave,
  onCancel,
}: {
  log: FoodLog;
  onSave: (data: { serving_size: number; note: string }) => Promise<void>;
  onCancel: () => void;
}) {
  const [servingSize, setServingSize] = useState(log.serving_size);
  const [note, setNote] = useState(log.note || "");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    await onSave({ serving_size: servingSize, note });
    setSaving(false);
  };

  const ratio = servingSize / 100;
  const previewCalories = Math.round(log.calories * ratio);

  return (
    <div className="mt-3 pt-3 border-t border-gray-100 space-y-3 animate-fade-in">

      {/* Serving size */}
      <div className="space-y-1">
        <div className="flex justify-between items-center">
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Serving size
          </label>
          <span className="text-sm font-semibold text-primary-600">
            {servingSize}g → {previewCalories} kcal
          </span>
        </div>
        <input
          type="range"
          min={50}
          max={500}
          step={10}
          value={servingSize}
          onChange={(e) => setServingSize(Number(e.target.value))}
          className="w-full accent-primary-600"
        />
      </div>

      {/* Note */}
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Add a note..."
        rows={2}
        className="w-full text-sm text-gray-700 placeholder:text-gray-300 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-primary-400"
      />

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={onCancel}
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-200 text-gray-500 text-sm hover:bg-gray-50 transition-colors"
        >
          <X className="w-3.5 h-3.5" />
          Cancel
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 transition-colors"
        >
          <Check className="w-3.5 h-3.5" />
          {saving ? "Saving..." : "Save changes"}
        </button>
      </div>

    </div>
  );
}

// ==========================================
// Main component
// ==========================================

export default function FoodLogCard({
  log,
  onDeleted,
  onUpdated,
}: FoodLogCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // ==========================================
  // Handlers
  // ==========================================

  const handleDelete = async () => {
    if (!confirm(`Delete "${log.food_name}" from your log?`)) return;

    setDeleting(true);
    try {
      await logsApi.deleteLog(log.id);
      toast.success("Log deleted");
      onDeleted?.();
    } catch {
      toast.error("Failed to delete log");
      setDeleting(false);
    }
  };

  const handleUpdate = async (data: {
    serving_size: number;
    note: string;
  }) => {
    try {
      await logsApi.updateLog(log.id, data);
      toast.success("Log updated");
      setEditing(false);
      onUpdated?.();
    } catch {
      toast.error("Failed to update log");
    }
  };

  // ==========================================
  // Render
  // ==========================================

  return (
    <div
      className={`
        bg-white rounded-2xl border border-gray-100 overflow-hidden
        transition-all duration-200 hover:shadow-sm
        ${deleting ? "opacity-50 pointer-events-none" : ""}
      `}
    >
      {/* Main row */}
      <div className="flex items-center gap-3 p-4">

        {/* Food image */}
        <div className="relative w-14 h-14 rounded-xl overflow-hidden bg-gray-100 shrink-0">
          {log.image_url ? (
            <Image
              src={log.image_url}
              alt={log.food_name}
              fill
              className="object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <Utensils className="w-6 h-6 text-gray-300" />
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="font-semibold text-gray-800 truncate">
                {log.food_name}
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                {/* Meal type badge */}
                <span
                  className={`
                    text-xs px-2 py-0.5 rounded-full border font-medium
                    ${MEAL_COLORS[log.meal_type] || "bg-gray-50 text-gray-500 border-gray-100"}
                  `}
                >
                  {MEAL_EMOJI[log.meal_type]} {log.meal_type}
                </span>

                {/* Time */}
                <span className="flex items-center gap-1 text-xs text-gray-400">
                  <Clock className="w-3 h-3" />
                  {format(parseISO(log.eaten_at), "h:mm a")}
                </span>
              </div>
            </div>

            {/* Calories */}
            <div className="text-right shrink-0">
              <p className="text-lg font-bold text-primary-600">
                {Math.round(log.total_calories)}
              </p>
              <p className="text-xs text-gray-400">kcal</p>
            </div>
          </div>

          {/* Serving size */}
          <p className="text-xs text-gray-400 mt-1">
            {log.serving_size}{log.serving_unit}
          </p>
        </div>

        {/* Expand toggle */}
        <button
          onClick={() => {
            setExpanded(!expanded);
            setEditing(false);
          }}
          className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors shrink-0"
        >
          {expanded
            ? <ChevronUp className="w-4 h-4" />
            : <ChevronDown className="w-4 h-4" />
          }
        </button>

      </div>

      {/* Expanded panel */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3 animate-fade-in">

          {/* Macros */}
          <div className="flex gap-2">
            <MacroPill
              label="Protein"
              value={log.total_protein}
              color="bg-green-50 text-green-700"
            />
            <MacroPill
              label="Carbs"
              value={log.total_carbohydrates}
              color="bg-blue-50 text-blue-700"
            />
            <MacroPill
              label="Fat"
              value={log.total_fat}
              color="bg-yellow-50 text-yellow-700"
            />
            {log.fiber !== null && (
              <MacroPill
                label="Fiber"
                value={log.fiber}
                color="bg-purple-50 text-purple-700"
              />
            )}
          </div>

          {/* Confidence */}
          {log.confidence !== null && (
            <div className="space-y-1">
              <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">
                AI Confidence
              </p>
              <ConfidenceBar confidence={log.confidence} />
            </div>
          )}

          {/* Note */}
          {log.note && !editing && (
            <div className="bg-gray-50 rounded-xl px-3 py-2">
              <p className="text-xs text-gray-400 mb-0.5">Note</p>
              <p className="text-sm text-gray-600">{log.note}</p>
            </div>
          )}

          {/* Edit form */}
          {editing && (
            <EditForm
              log={log}
              onSave={handleUpdate}
              onCancel={() => setEditing(false)}
            />
          )}

          {/* Action buttons */}
          {!editing && (
            <div className="flex gap-2 pt-1">
              <button
                onClick={() => setEditing(true)}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-200 text-gray-500 text-xs font-medium hover:bg-gray-50 transition-colors"
              >
                <Edit2 className="w-3.5 h-3.5" />
                Edit
              </button>
              <button
                onClick={handleDelete}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-red-100 text-red-500 text-xs font-medium hover:bg-red-50 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Delete
              </button>
            </div>
          )}

        </div>
      )}

    </div>
  );
}