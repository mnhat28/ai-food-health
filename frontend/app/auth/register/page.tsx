"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { register } from "@/lib/auth";
import Link from "next/link";
import {
  Eye,
  EyeOff,
  Loader2,
  Mail,
  Lock,
  User,
  Leaf,
  Check,
} from "lucide-react";

// ==========================================
// Types
// ==========================================

interface FormErrors {
  email?: string;
  username?: string;
  password?: string;
  confirmPassword?: string;
  general?: string;
}

// ==========================================
// Input field (reused from login)
// ==========================================

function InputField({
  label,
  type,
  value,
  onChange,
  error,
  placeholder,
  icon,
  rightElement,
  hint,
  disabled,
}: {
  label: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
  error?: string;
  placeholder?: string;
  icon: React.ReactNode;
  rightElement?: React.ReactNode;
  hint?: string;
  disabled?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium text-gray-700">{label}</label>
      <div
        className={`
          flex items-center gap-3 bg-gray-50 border rounded-xl px-4 py-3
          transition-all focus-within:bg-white focus-within:border-primary-400
          focus-within:ring-2 focus-within:ring-primary-100
          ${error ? "border-red-300 bg-red-50" : "border-gray-200"}
        `}
      >
        <span className={`shrink-0 ${error ? "text-red-400" : "text-gray-400"}`}>
          {icon}
        </span>
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className="flex-1 text-sm text-gray-700 placeholder:text-gray-400 bg-transparent focus:outline-none disabled:opacity-60"
        />
        {rightElement}
      </div>
      {error && (
        <p className="text-xs text-red-500">{error}</p>
      )}
      {hint && !error && (
        <p className="text-xs text-gray-400">{hint}</p>
      )}
    </div>
  );
}

// ==========================================
// Password strength
// ==========================================

function PasswordStrength({ password }: { password: string }) {
  if (!password) return null;

  const checks = [
    { label: "At least 8 characters", pass: password.length >= 8 },
    { label: "Contains a number", pass: /\d/.test(password) },
    { label: "Contains uppercase", pass: /[A-Z]/.test(password) },
  ];

  const passCount = checks.filter((c) => c.pass).length;
  const strengthColor =
    passCount === 3
      ? "bg-green-500"
      : passCount === 2
      ? "bg-yellow-400"
      : "bg-red-400";

  return (
    <div className="space-y-2 animate-fade-in">
      {/* Strength bar */}
      <div className="flex gap-1">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-all duration-300 ${
              i <= passCount ? strengthColor : "bg-gray-200"
            }`}
          />
        ))}
      </div>

      {/* Checklist */}
      <div className="space-y-1">
        {checks.map((check) => (
          <div key={check.label} className="flex items-center gap-2">
            <div
              className={`w-4 h-4 rounded-full flex items-center justify-center transition-all ${
                check.pass ? "bg-green-500" : "bg-gray-200"
              }`}
            >
              {check.pass && <Check className="w-2.5 h-2.5 text-white" />}
            </div>
            <span
              className={`text-xs transition-colors ${
                check.pass ? "text-green-600" : "text-gray-400"
              }`}
            >
              {check.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ==========================================
// Step indicator
// ==========================================

function StepIndicator({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center gap-2 justify-center">
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          className={`h-1.5 rounded-full transition-all duration-300 ${
            i < current
              ? "bg-primary-600 w-6"
              : i === current
              ? "bg-primary-400 w-4"
              : "bg-gray-200 w-4"
          }`}
        />
      ))}
    </div>
  );
}

// ==========================================
// Main page
// ==========================================

export default function RegisterPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [loading, setLoading] = useState(false);

  // ==========================================
  // Validation per step
  // ==========================================

  const validateStep0 = (): boolean => {
    const newErrors: FormErrors = {};

    if (!email.trim()) {
      newErrors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = "Enter a valid email address";
    }

    if (!username.trim()) {
      newErrors.username = "Username is required";
    } else if (username.length < 3) {
      newErrors.username = "Username must be at least 3 characters";
    } else if (!/^[a-zA-Z0-9_]+$/.test(username)) {
      newErrors.username = "Only letters, numbers and underscores allowed";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateStep1 = (): boolean => {
    const newErrors: FormErrors = {};

    if (!password) {
      newErrors.password = "Password is required";
    } else if (password.length < 6) {
      newErrors.password = "Password must be at least 6 characters";
    }

    if (!confirmPassword) {
      newErrors.confirmPassword = "Please confirm your password";
    } else if (password !== confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // ==========================================
  // Navigation
  // ==========================================

  const handleNext = () => {
    if (step === 0 && validateStep0()) {
      setErrors({});
      setStep(1);
    }
  };

  const handleBack = () => {
    setErrors({});
    setStep(0);
  };

  // ==========================================
  // Submit
  // ==========================================

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateStep1()) return;

    setLoading(true);
    setErrors({});

    try {
      await register(email, username, password, fullName || undefined);
      router.replace("/");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Registration failed";
      setErrors({ general: message });
    } finally {
      setLoading(false);
    }
  };

  // ==========================================
  // Render
  // ==========================================

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-emerald-50 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm space-y-8">

        {/* Logo */}
        <div className="text-center">
          <div className="w-16 h-16 bg-primary-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-primary-200">
            <Leaf className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-800">Create account</h1>
          <p className="text-sm text-gray-400 mt-1">
            Start tracking your nutrition today
          </p>
        </div>

        {/* Step indicator */}
        <StepIndicator current={step} total={2} />

        {/* General error */}
        {errors.general && (
          <div className="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-3 rounded-xl animate-fade-in">
            {errors.general}
          </div>
        )}

        {/* Step 0 — Account info */}
        {step === 0 && (
          <div className="space-y-4 animate-fade-in">
            <div className="space-y-1">
              <h2 className="text-base font-semibold text-gray-700">
                Account information
              </h2>
              <p className="text-xs text-gray-400">
                Step 1 of 2 — Enter your basic details
              </p>
            </div>

            <InputField
              label="Full name"
              type="text"
              value={fullName}
              onChange={setFullName}
              placeholder="John Doe (optional)"
              icon={<User className="w-4 h-4" />}
              disabled={loading}
            />

            <InputField
              label="Email"
              type="email"
              value={email}
              onChange={setEmail}
              error={errors.email}
              placeholder="you@example.com"
              icon={<Mail className="w-4 h-4" />}
              disabled={loading}
            />

            <InputField
              label="Username"
              type="text"
              value={username}
              onChange={setUsername}
              error={errors.username}
              placeholder="john_doe"
              icon={<User className="w-4 h-4" />}
              hint="Letters, numbers and underscores only"
              disabled={loading}
            />

            <button
              onClick={handleNext}
              className="w-full py-3 rounded-xl bg-primary-600 text-white font-semibold text-sm hover:bg-primary-700 active:scale-[0.98] transition-all mt-2"
            >
              Continue
            </button>
          </div>
        )}

        {/* Step 1 — Password */}
        {step === 1 && (
          <form onSubmit={handleSubmit} className="space-y-4 animate-fade-in">
            <div className="space-y-1">
              <h2 className="text-base font-semibold text-gray-700">
                Set your password
              </h2>
              <p className="text-xs text-gray-400">
                Step 2 of 2 — Choose a secure password
              </p>
            </div>

            <InputField
              label="Password"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={setPassword}
              error={errors.password}
              placeholder="Create a strong password"
              icon={<Lock className="w-4 h-4" />}
              disabled={loading}
              rightElement={
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  {showPassword
                    ? <EyeOff className="w-4 h-4" />
                    : <Eye className="w-4 h-4" />
                  }
                </button>
              }
            />

            {/* Password strength */}
            <PasswordStrength password={password} />

            <InputField
              label="Confirm password"
              type={showConfirm ? "text" : "password"}
              value={confirmPassword}
              onChange={setConfirmPassword}
              error={errors.confirmPassword}
              placeholder="Repeat your password"
              icon={<Lock className="w-4 h-4" />}
              disabled={loading}
              rightElement={
                <button
                  type="button"
                  onClick={() => setShowConfirm(!showConfirm)}
                  className="shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  {showConfirm
                    ? <EyeOff className="w-4 h-4" />
                    : <Eye className="w-4 h-4" />
                  }
                </button>
              }
            />

            {/* Actions */}
            <div className="flex gap-3 mt-2">
              <button
                type="button"
                onClick={handleBack}
                disabled={loading}
                className="px-5 py-3 rounded-xl border border-gray-200 text-gray-500 text-sm font-medium hover:bg-gray-50 transition-colors disabled:opacity-60"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 py-3 rounded-xl bg-primary-600 text-white font-semibold text-sm hover:bg-primary-700 active:scale-[0.98] transition-all disabled:opacity-60 disabled:pointer-events-none flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Creating account...
                  </>
                ) : (
                  "Create account"
                )}
              </button>
            </div>

          </form>
        )}

        {/* Footer */}
        <p className="text-center text-sm text-gray-400">
          Already have an account?{" "}
          <Link
            href="/auth/login"
            className="text-primary-600 font-medium hover:text-primary-700"
          >
            Sign in
          </Link>
        </p>

      </div>
    </div>
  );
}