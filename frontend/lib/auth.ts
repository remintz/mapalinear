import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

// Extend the session and JWT to include our custom fields
declare module "next-auth" {
  interface Session {
    accessToken?: string;
    authError?: string;
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
    authError?: string;
  }
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  trustHost: true,
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
        const backendUrl = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api"}/auth/google`;
        console.log("[Auth] Authenticating with backend:", backendUrl);

        try {
          const response = await fetch(backendUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: account.id_token }),
          });

          console.log("[Auth] Backend response status:", response.status);

          if (response.ok) {
            const data = await response.json();
            token.accessToken = data.access_token;
            token.userId = data.user.id;
            token.isAdmin = data.user.is_admin;
            console.log("[Auth] Successfully authenticated with backend, userId:", data.user.id);
          } else {
            const errorText = await response.text();
            console.error("[Auth] Backend authentication failed:", response.status, errorText);
            // Store error info for debugging
            token.authError = `Backend auth failed: ${response.status}`;
          }
        } catch (error) {
          console.error("[Auth] Failed to connect to backend:", error);
          token.authError = `Connection failed: ${error instanceof Error ? error.message : 'Unknown error'}`;
        }
      }

      // Log if we don't have a valid token after the callback
      if (!token.accessToken && !account) {
        console.warn("[Auth] No access token in session (may need to re-login)");
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
      // Pass auth error to session so it can be displayed to user
      if (typeof token.authError === "string") {
        session.authError = token.authError;
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
