import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ACCESS_TOKEN_COOKIE_NAME, REFRESH_TOKEN_COOKIE_NAME } from "@/lib/auth/cookies";

export async function POST(): Promise<NextResponse> {
  const cookieStore = await cookies();
  cookieStore.delete(ACCESS_TOKEN_COOKIE_NAME);
  cookieStore.delete(REFRESH_TOKEN_COOKIE_NAME);
  return NextResponse.json({ success: true });
}
