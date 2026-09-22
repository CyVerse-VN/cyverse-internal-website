"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronDown, LogOut, Settings, Shield } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { logoutAction } from "@/features/auth/actions";
import type { AuthUser } from "@/lib/auth/types";

function userInitials(user: AuthUser): string {
  return user.display_name
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function AccountMenu({ user }: { user: AuthUser }) {
  const router = useRouter();
  const [isSigningOut, setIsSigningOut] = useState(false);
  const initials = userInitials(user);

  const handleSignOut = async () => {
    if (isSigningOut) return;
    setIsSigningOut(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } catch {
      // Ignore network errors
    }
    try {
      await logoutAction();
    } catch {
      // Ignore NEXT_REDIRECT error
    }
    router.replace("/login");
    router.refresh();
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="flex min-w-[190px] items-center gap-2.5 rounded-xl border border-transparent p-1.5 transition-all hover:border-slate-200 hover:bg-white hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30 text-left"
        aria-label="Open account menu"
      >
        <Avatar className="h-9 w-9 ring-2 ring-blue-500/20">
          <AvatarFallback>{initials}</AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <strong className="block truncate text-sm font-semibold text-slate-800">
            {user.display_name}
          </strong>
          <small className="block truncate text-xs text-slate-500">
            {user.role === "admin" ? "Administrator" : user.team ?? "Member"}
          </small>
        </div>
        <ChevronDown className="h-4 w-4 text-slate-400 transition-transform duration-200" />
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-64 p-2" align="end">
        <DropdownMenuLabel className="p-2 font-normal">
          <div className="flex items-center gap-3">
            <Avatar className="h-10 w-10">
              <AvatarFallback className="text-sm font-bold">{initials}</AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-slate-900 leading-tight">
                {user.display_name}
              </p>
              <p className="truncate text-xs text-slate-500 mt-0.5">@{user.username}</p>
            </div>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link
            className="flex w-full items-center gap-2.5 px-2.5 py-2 cursor-pointer"
            href="/settings/account"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
              <Settings className="h-4 w-4" />
            </div>
            <div>
              <strong className="block text-sm font-medium text-slate-800">Account settings</strong>
              <small className="block text-xs text-slate-500">Profile & security</small>
            </div>
          </Link>
        </DropdownMenuItem>
        {user.role === "admin" && (
          <DropdownMenuItem asChild>
            <Link
              className="flex w-full items-center gap-2.5 px-2.5 py-2 cursor-pointer"
              href="/admin/users"
            >
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
                <Shield className="h-4 w-4" />
              </div>
              <div>
                <strong className="block text-sm font-medium text-slate-800">User Management</strong>
                <small className="block text-xs text-slate-500">Manage accounts & roles</small>
              </div>
            </Link>
          </DropdownMenuItem>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="flex w-full items-center gap-2.5 px-2.5 py-2 text-red-600 focus:bg-red-50 focus:text-red-700 cursor-pointer"
          disabled={isSigningOut}
          onSelect={(event) => {
            event.preventDefault();
            void handleSignOut();
          }}
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-red-50 text-red-600">
            <LogOut className="h-4 w-4" />
          </div>
          <div>
            <strong className="block text-sm font-medium">
              {isSigningOut ? "Signing out…" : "Sign out"}
            </strong>
            <small className="block text-xs text-red-400">End this session</small>
          </div>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

