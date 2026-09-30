import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "Resolve", description: "Trusted organisational knowledge" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
