"use client";
import React, { useState } from "react";
import { Radar, Lock, User, KeyRound, ShieldAlert, ArrowLeft, CheckCircle2 } from "lucide-react";

interface LoginModalProps {
  onLoginSuccess: (username: string) => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("لطفاً نام کاربری و کلمه عبور را وارد نمایید.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim(), password: password.trim() }),
      });

      let data: any = {};
      try {
        data = await res.json();
      } catch {
        const text = await res.text();
        data = { detail: text || "خطا در دریافت پاسخ از سرور." };
      }

      if (!res.ok) {
        throw new Error(data.detail || "نام کاربری یا رمز عبور نامعتبر است.");
      }

      // Save token in localStorage for persistent 30-day cross-session access
      if (data.token) {
        localStorage.setItem("radar_auth_token", data.token);
        localStorage.setItem("radar_auth_user", data.username);
        localStorage.setItem("radar_auth_login_at", new Date().toISOString());
      }

      onLoginSuccess(data.username);
    } catch (err: any) {
      setError(err.message || "خطا در برقراری ارتباط با سرور.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(5, 8, 15, 0.92)",
        backdropFilter: "blur(12px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "1rem",
        fontFamily: "var(--font-vazir, system-ui, sans-serif)",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "430px",
          backgroundColor: "#0f172a",
          border: "1px solid #334155",
          borderRadius: "16px",
          padding: "2.25rem",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.75), 0 0 30px rgba(34, 197, 94, 0.15)",
          color: "#f8fafc",
          position: "relative",
        }}
      >
        {/* Logo & Header */}
        <div style={{ textAlign: "center", marginBottom: "1.75rem" }}>
          <div
            style={{
              width: "56px",
              height: "56px",
              margin: "0 auto 1rem",
              borderRadius: "14px",
              backgroundColor: "rgba(34, 197, 94, 0.15)",
              border: "1px solid rgba(34, 197, 94, 0.35)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#22c55e",
              boxShadow: "0 0 20px rgba(34, 197, 94, 0.25)",
            }}
          >
            <Radar size={30} />
          </div>
          <h2 style={{ fontSize: "1.35rem", fontWeight: 900, marginBottom: "0.4rem" }}>
            سامانه رادار بازار سرمایه
          </h2>
          <p style={{ fontSize: "0.82rem", color: "#94a3b8", lineHeight: 1.5 }}>
            ورود به پنل پایش هوشمند، مدیریت معاملات و پورتفوی ۱ میلیارد تومانی
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.6rem",
              backgroundColor: "rgba(239, 68, 68, 0.15)",
              border: "1px solid rgba(239, 68, 68, 0.35)",
              color: "#fca5a5",
              padding: "0.75rem 1rem",
              borderRadius: "8px",
              fontSize: "0.82rem",
              marginBottom: "1.25rem",
            }}
          >
            <ShieldAlert size={18} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.82rem", fontWeight: 700, color: "#cbd5e1", marginBottom: "0.4rem" }}>
              نام کاربری
            </label>
            <div style={{ position: "relative" }}>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="نام کاربری (پیش‌فرض: admin)"
                style={{
                  width: "100%",
                  padding: "0.75rem 1rem 0.75rem 2.5rem",
                  backgroundColor: "#1e293b",
                  border: "1px solid #475569",
                  borderRadius: "8px",
                  color: "#f8fafc",
                  fontSize: "0.9rem",
                  outline: "none",
                  fontFamily: "inherit",
                }}
                disabled={loading}
                autoFocus
              />
              <User size={18} style={{ position: "absolute", left: "0.85rem", top: "50%", transform: "translateY(-50%)", color: "#64748b" }} />
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.82rem", fontWeight: 700, color: "#cbd5e1", marginBottom: "0.4rem" }}>
              کلمه عبور
            </label>
            <div style={{ position: "relative" }}>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="کلمه عبور امن"
                style={{
                  width: "100%",
                  padding: "0.75rem 1rem 0.75rem 2.5rem",
                  backgroundColor: "#1e293b",
                  border: "1px solid #475569",
                  borderRadius: "8px",
                  color: "#f8fafc",
                  fontSize: "0.9rem",
                  outline: "none",
                  fontFamily: "inherit",
                }}
                disabled={loading}
              />
              <KeyRound size={18} style={{ position: "absolute", left: "0.85rem", top: "50%", transform: "translateY(-50%)", color: "#64748b" }} />
            </div>
          </div>

          {/* Session Duration Badge */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              backgroundColor: "rgba(30, 41, 59, 0.7)",
              padding: "0.5rem 0.75rem",
              borderRadius: "6px",
              fontSize: "0.74rem",
              color: "#94a3b8",
            }}
          >
            <CheckCircle2 size={14} color="#22c55e" />
            <span>نشست پایدار ۳۰ روزه فعال است (بدون نیاز به لاگین مکرر)</span>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: "0.5rem",
              padding: "0.85rem 1.25rem",
              backgroundColor: loading ? "#334155" : "#22c55e",
              color: "#ffffff",
              border: "none",
              borderRadius: "8px",
              fontWeight: 800,
              fontSize: "0.92rem",
              cursor: loading ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "0.5rem",
              boxShadow: "0 4px 14px rgba(34, 197, 94, 0.3)",
              transition: "all 0.2s ease",
              fontFamily: "inherit",
            }}
          >
            <Lock size={16} />
            <span>{loading ? "در حال اعتبارسنجی..." : "ورود امن به سامانه"}</span>
          </button>
        </form>
      </div>
    </div>
  );
};
