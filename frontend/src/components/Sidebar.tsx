"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageCircle,
  CheckSquare,
  FolderKanban,
  FileText,
  Clock,
} from "lucide-react";
import { clsx } from "clsx";

const navigation = [
  { name: "チャット", href: "/", icon: MessageCircle },
  { name: "タスク", href: "/tasks", icon: CheckSquare },
  { name: "プロジェクト", href: "/projects", icon: FolderKanban },
  { name: "Draft", href: "/drafts", icon: FileText },
  { name: "フォローアップ", href: "/followup", icon: Clock },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-6">
        <h1 className="text-2xl font-bold text-gray-900">MOS</h1>
        <p className="text-sm text-gray-500 mt-1">
          Management Ourselves System
        </p>
      </div>

      <nav className="flex-1 px-3 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.name}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-700 hover:bg-gray-100 hover:text-gray-900"
              )}
            >
              <Icon className="w-5 h-5" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-200">
        <p className="text-xs text-gray-500">
          Phase 1 MVP - 2026-01-21
        </p>
      </div>
    </aside>
  );
}
