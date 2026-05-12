import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "民医智问 - Ethno Med AI",
  description: "少数民族医药智能问答系统",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">{children}</body>
    </html>
  );
}
