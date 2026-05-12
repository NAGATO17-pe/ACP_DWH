import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Correo inválido"),
  password: z.string().min(8, "Mínimo 8 caracteres"),
});

export type LoginInput = z.infer<typeof loginSchema>;

/** Shape expected from FastAPI /auth/login. */
export const loginResponseSchema = z.object({
  access_token: z.string().min(1),
  token_type: z.literal("bearer").optional(),
});

export type LoginResponse = z.infer<typeof loginResponseSchema>;
