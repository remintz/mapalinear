import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

// Extend the session and JWT to include our custom fields
declare module "next-auth" {
  interface Session {
    accessToken?: string;
    user: {
      id: string;
      email?: string | null;
      name?: string | null;
      image?: string | null;
      isAdmin?: boolean;
    };
  }

  interface JWT {
    accessToken?: string;
    userId?: string;
    isAdmin?: boolean;
  }
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async jwt({ token, account }) {
      // On initial sign in, exchange Google token with our backend
      if (account?.id_token) {
        try {
          const response = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api"}/auth/google`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ token: account.id_token }),
            }
          );

          if (response.ok) {
            const data = await response.json();
            token.accessToken = data.access_token;
            token.userId = data.user.id;
            token.isAdmin = data.user.is_admin;
          }
        } catch (error) {
          console.error("Failed to authenticate with backend:", error);
        }
      }
      return token;
    },
    async session({ session, token }) {
      // Pass the backend token to the session
      if (typeof token.accessToken === "string") {
        session.accessToken = token.accessToken;
      }
      if (session.user && typeof token.userId === "string") {
        session.user.id = token.userId;
      }
      if (session.user && typeof token.isAdmin === "boolean") {
        session.user.isAdmin = token.isAdmin;
      }
      return session;
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
  session: {
    strategy: "jwt",
  },
});
