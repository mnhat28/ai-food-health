"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { foodApi, logsApi } from "@/lib/api";
import {
  Upload,
  Camera,
  X,
  CheckCircle,
  AlertCircle,
  Loader2,
  RefreshCw,
} from "lucide-react";
import Image from "next/image";
import toast from "react-hot-toast";

// ==========================================
// Types
// ==========================================

interface PredictionResult {
  food_name: string;
  food_name_en: string;
  confidence: float;
  calories: number;
  protein: number | null;
  carbohydrates: number | null;
  fat: number | null;
  fiber: number | null;
  serving_size: number;
  top_predictions: Array<{
    rank: number;
    label: string;
    confidence: number;
  }>;
}

interface FoodUploaderProps {
  onLogCreated?: () => void;
}

type MealType = "breakfast" | "lunch" | "dinner" | "snack";

const MEAL_TYPES: { value: MealType; label: string; emoji: string }[] = [
  { value: "breakfast", label: "Breakfast", emoji: "🌅" },
  { value: "lunch", label: "Lunch", emoji: "☀️" },
  { value: "dinner", label: "Dinner", emoji: "🌙" },
  { value: "snack", label: "Snack", emoji: "🍎" },
];

// ==========================================
// Confidence badge
// ==========================================

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color =
    pct >= 80
      ? "bg-green-100 text-green-700"
      : pct >= 60
      ? "bg-yellow-100 text-yellow-700"
      : "bg-red-100 text-red-700";

  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${color}`}>
      {pct}% confidence
    </span>
  );
}

// ==========================================
// Macro badge
// ==========================================

function MacroBadge({
  label,
  value,
  unit,
  color,
}: {
  label: string;
  value: number | null;
  unit: string;
  color: string;
}) {
  if (value === null) return null;
  return (
    <div className={`flex flex-col items-center px-4 py-3 rounded-xl ${color}`}>
      <span className="text-lg font-bold">
        {Math.round(value)}{unit}
      </span>
      <span className="text-xs text-gray-500 mt-0.5">{label}</span>
    </div>
  );
}

// ==========================================
// Main component
// ==========================================

export default function FoodUploader({ onLogCreated }: FoodUploaderProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [mealType, setMealType] = useState<MealType>("lunch");
  const [servingSize, setServingSize] = useState<number>(100);
  const [note, setNote] = useState<string>("");
  const [step, setStep] = useState<"upload" | "analyzing" | "result" | "saving">("upload");
  const [error, setError] = useState<string | null>(null);

  // ==========================================
  // Dropzone
  // ==========================================

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const dropped = acceptedFiles[0];
    if (!dropped) return;

    setFile(dropped);
    setPreview(URL.createObjectURL(dropped));
    setResult(null);
    setError(null);
    setStep("upload");
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [".jpg", ".jpeg", ".png", ".webp"] },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024,
    onDropRejected: (rejections) => {
      const reason = rejections[0]?.errors[0]?.message || "Invalid file";
      setError(reason);
      toast.error(reason);
    },
  });

  // ==========================================
  // Analyze
  // ==========================================

  const handleAnalyze = async () => {
    if (!file) return;

    setStep("analyzing");
    setError(null);

    try {
      const data = await foodApi.analyzeImage(file);
      setResult(data);
      setServingSize(data.serving_size || 100);
      setStep("result");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to analyze image";
      setError(message);
      setStep("upload");
      toast.error("Failed to analyze image. Please try again.");
    }
  };

  // ==========================================
  // Save log
  // ==========================================

  const handleSaveLog = async () => {
    if (!result) return;

    setStep("saving");

    try {
      const ratio = servingSize / 100;

      await logsApi.createLog({
        food_name: result.food_name,
        food_name_en: result.food_name_en,
        confidence: result.confidence,
        calories: result.calories,
        protein: result.protein,
        carbohydrates: result.carbohydrates,
        fat: result.fat,
        fiber: result.fiber,
        serving_size: servingSize,
        meal_type: mealType,
        eaten_at: new Date().toISOString(),
        note: note || null,
        ml_raw: result.top_predictions,
      });

      toast.success(`${result.food_name} logged successfully!`);
      handleReset();
      onLogCreated?.();
    } catch {
      setStep("result");
      toast.error("Failed to save log. Please try again.");
    }
  };

  // ==========================================
  // Reset
  // ==========================================

  const handleReset = () => {
    setPreview(null);
    setFile(null);
    setResult(null);
    setNote("");
    setServingSize(100);
    setStep("upload");
    setError(null);
  };

  // ==========================================
  // Computed values
  // ==========================================

  const ratio = servingSize / 100;
  const totalCalories = result ? Math.round(result.calories * ratio) : 0;
  const totalProtein = result?.protein ? Math.round(result.protein * ratio) : null;
  const totalCarbs = result?.carbohydrates ? Math.round(result.carbohydrates * ratio) : null;
  const totalFat = result?.fat ? Math.round(result.fat * ratio) : null;

  // ==========================================
  // Render
  // ==========================================

  return (
    <div className="w-full max-w-lg mx-auto space-y-4">

      {/* Drop zone */}
      {!preview && (
        <div
          {...getRootProps()}
          className={`
            relative border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer
            transition-all duration-200
            ${isDragActive
              ? "border-primary-500 bg-primary-50 scale-[1.02]"
              : "border-gray-200 bg-gray-50 hover:border-primary-400 hover:bg-primary-50"
            }
          `}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-full bg-primary-100 flex items-center justify-center">
              <Upload className="w-7 h-7 text-primary-600" />
            </div>
            <div>
              <p className="font-semibold text-gray-700">
                {isDragActive ? "Drop your image here" : "Upload a food photo"}
              </p>
              <p className="text-sm text-gray-400 mt-1">
                Drag & drop or click to browse — JPG, PNG, WebP up to 10MB
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <Camera className="w-3.5 h-3.5" />
              <span>Or take a photo with your camera</span>
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 px-4 py-3 rounded-xl">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Preview */}
      {preview && (
        <div className="relative rounded-2xl overflow-hidden bg-gray-100 aspect-square">
          <Image
            src={preview}
            alt="Food preview"
            fill
            className="object-cover"
          />

          {/* Reset button */}
          <button
            onClick={handleReset}
            className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/50 flex items-center justify-center hover:bg-black/70 transition-colors"
          >
            <X className="w-4 h-4 text-white" />
          </button>

          {/* Analyzing overlay */}
          {step === "analyzing" && (
            <div className="absolute inset-0 bg-black/40 flex flex-col items-center justify-center gap-3">
              <Loader2 className="w-10 h-10 text-white animate-spin" />
              <p className="text-white font-medium text-sm">
                Analyzing your food...
              </p>
            </div>
          )}
        </div>
      )}

      {/* Analyze button */}
      {preview && step === "upload" && (
        <button
          onClick={handleAnalyze}
          className="w-full py-3 rounded-xl bg-primary-600 text-white font-semibold hover:bg-primary-700 active:scale-[0.98] transition-all"
        >
          Analyze Food
        </button>
      )}

      {/* Result */}
      {step === "result" && result && (
        <div className="space-y-4 animate-fade-in">

          {/* Food name + confidence */}
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-xl font-bold text-gray-800">
                {result.food_name}
              </h3>
              <p className="text-sm text-gray-400">{result.food_name_en}</p>
            </div>
            <ConfidenceBadge confidence={result.confidence} />
          </div>

          {/* Top predictions */}
          {result.top_predictions.length > 1 && (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">
                Other possibilities
              </p>
              {result.top_predictions.slice(1, 4).map((p) => (
                <div
                  key={p.rank}
                  className="flex items-center justify-between text-sm text-gray-500 bg-gray-50 px-3 py-2 rounded-lg"
                >
                  <span>{p.label.replace(/_/g, " ")}</span>
                  <span className="text-xs text-gray-400">
                    {Math.round(p.confidence * 100)}%
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Serving size */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              Serving size
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={50}
                max={500}
                step={10}
                value={servingSize}
                onChange={(e) => setServingSize(Number(e.target.value))}
                className="flex-1 accent-primary-600"
              />
              <span className="text-sm font-semibold text-gray-700 w-16 text-right">
                {servingSize}g
              </span>
            </div>
          </div>

          {/* Calories */}
          <div className="flex items-center justify-center bg-primary-50 rounded-2xl py-5">
            <div className="text-center">
              <p className="text-4xl font-bold text-primary-600">
                {totalCalories}
              </p>
              <p className="text-sm text-gray-500 mt-1">kcal</p>
            </div>
          </div>

          {/* Macros */}
          <div className="grid grid-cols-3 gap-3">
            <MacroBadge
              label="Protein"
              value={totalProtein}
              unit="g"
              color="bg-green-50"
            />
            <MacroBadge
              label="Carbs"
              value={totalCarbs}
              unit="g"
              color="bg-blue-50"
            />
            <MacroBadge
              label="Fat"
              value={totalFat}
              unit="g"
              color="bg-yellow-50"
            />
          </div>

          {/* Meal type */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              Meal type
            </label>
            <div className="grid grid-cols-4 gap-2">
              {MEAL_TYPES.map((m) => (
                <button
                  key={m.value}
                  onClick={() => setMealType(m.value)}
                  className={`
                    flex flex-col items-center gap-1 py-2 rounded-xl text-xs font-medium transition-all
                    ${mealType === m.value
                      ? "bg-primary-600 text-white"
                      : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                    }
                  `}
                >
                  <span className="text-base">{m.emoji}</span>
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          {/* Note */}
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Add a note (optional)..."
            rows={2}
            className="w-full text-sm text-gray-700 placeholder:text-gray-300 bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 resize-none focus:outline-none focus:ring-2 focus:ring-primary-400"
          />

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={handleReset}
              className="flex items-center gap-2 px-4 py-3 rounded-xl border border-gray-200 text-gray-500 text-sm font-medium hover:bg-gray-50 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Retake
            </button>
            <button
              onClick={handleSaveLog}
              disabled={step === "saving"}
              className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-primary-600 text-white font-semibold hover:bg-primary-700 active:scale-[0.98] transition-all disabled:opacity-60"
            >
              {step === "saving" ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4" />
                  Save to Log
                </>
              )}
            </button>
          </div>

        </div>
      )}

    </div>
  );
}