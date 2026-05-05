"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/auth";
import Link from "next/link";
import {
  Eye,
  EyeOff,
  Loader2,
  Mail,
  Lock,
  Leaf,
} from "lucide-react";

// ==========================================
// Types
// ==========================================

interface FormErrors {
  email?: string;
  password?: string;
  general?: string;
}

// ==========================================
// Input field
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
        <p className="text-xs text-red-500 flex items-center gap-1">
          {error}
        </p>
      )}
    </div>
  );
}

// ==========================================
// Main page
// ==========================================

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [loading, setLoading] = useState(false);

  // ==========================================
  // Validation
  // ==========================================

  const validate = (): boolean => {
    const newErrors: FormErrors = {};

    if (!email.trim()) {
      newErrors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = "Enter a valid email address";
    }

    if (!password) {
      newErrors.password = "Password is required";
    } else if (password.length < 6) {
      newErrors.password = "Password must be at least 6 characters";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // ==========================================
  // Submit
  // ==========================================

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    setErrors({});

    try {
      await login(email, password);
      router.replace("/");
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Invalid email or password";
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
          <h1 className="text-2xl font-bold text-gray-800">Welcome back</h1>
          <p className="text-sm text-gray-400 mt-1">
            Sign in to continue tracking your nutrition
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">

          {/* General error */}
          {errors.general && (
            <div className="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-3 rounded-xl animate-fade-in">
              {errors.general}
            </div>
          )}

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
            label="Password"
            type={showPassword ? "text" : "password"}
            value={password}
            onChange={setPassword}
            error={errors.password}
            placeholder="Enter your password"
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

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-primary-600 text-white font-semibold text-sm hover:bg-primary-700 active:scale-[0.98] transition-all disabled:opacity-60 disabled:pointer-events-none flex items-center justify-center gap-2 mt-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Signing in...
              </>
            ) : (
              "Sign in"
            )}
          </button>

        </form>

        {/* Footer */}
        <div className="text-center space-y-3">
          <p className="text-sm text-gray-400">
            Don&apos;t have an account?{" "}
            <Link
              href="/auth/register"
              className="text-primary-600 font-medium hover:text-primary-700"
            >
              Create one
            </Link>
          </p>
        </div>

      </div>
    </div>
  );
}