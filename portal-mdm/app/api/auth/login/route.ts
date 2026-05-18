import { NextResponse } from "next/server";
import { apiFetch, ApiError } from "@/lib/api/client";
import {
  loginResponseSchema,
  loginSchema,
  type LoginResponse,
} from "@/lib/schemas/auth";
import { JWT_COOKIE_NAME } from "@/lib/auth/session";

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Cuerpo inválido" }, { status: 400 });
  }

  const parsed = loginSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      { detail: parsed.error.issues[0]?.message ?? "Datos inválidos" },
      { status: 400 },
    );
  }

  try {
    const data = await apiFetch<LoginResponse>("/auth/login", {
      method: "POST",
      body: parsed.data,
    });
    const tokenData = loginResponseSchema.parse(data);

    const response = NextResponse.json({ ok: true });
    response.cookies.set(JWT_COOKIE_NAME, tokenData.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 8, // 8 horas
    });
    return response;
  } catch (err) {
    if (err instanceof ApiError) {
      return NextResponse.json({ detail: err.message }, { status: err.status });
    }
    return NextResponse.json(
      { detail: "Error inesperado al iniciar sesión" },
      { status: 500 },
    );
  }
}
