import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "رادار بازار سرمایه ایران — پلتفرم تخصصی پویش و کالیبراسیون فرصت‌های معاملاتی",
  description: "سامانه رادار کمی بازار بورس اوراق بهادار تهران، کالیبراسیون احتمال سود، شبیه‌ساز بک‌تست و معاملات آزمایشی.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fa" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
