import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider, useAuth } from "@/lib/auth-context";
import { useRouter, usePathname } from "next/navigation";

// Mock next/navigation
const mockPush = jest.fn();
const mockReplace = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
  usePathname: jest.fn(),
}));

// Mock fetch
global.fetch = jest.fn();

// Test component that uses auth
function TestComponent() {
  const auth = useAuth();

  return (
    <div>
      <div data-testid="loading">{auth.loading ? "loading" : "not-loading"}</div>
      <div data-testid="user">{auth.user ? auth.user.email : "no-user"}</div>
      <div data-testid="authenticated">{auth.isAuthenticated ? "yes" : "no"}</div>
      <div data-testid="admin">{auth.isAdmin ? "yes" : "no"}</div>
      <div data-testid="super-admin">{auth.isSuperAdmin ? "yes" : "no"}</div>
      <div data-testid="requires-setup">{auth.requiresSetup ? "yes" : "no"}</div>
      {auth.error && <div data-testid="error">{auth.error}</div>}
      <button onClick={() => auth.login("test@example.com", "password")}>Login</button>
      <button onClick={() => auth.logout()}>Logout</button>
    </div>
  );
}

describe("AuthContext", () => {
  const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
      replace: mockReplace,
      prefetch: jest.fn(),
      back: jest.fn(),
    });
    (usePathname as jest.Mock).mockReturnValue("/");
  });

  describe("useAuth hook", () => {
    it("throws error when used outside provider", () => {
      // Suppress console.error for this test
      const consoleSpy = jest.spyOn(console, "error").mockImplementation();

      expect(() => {
        render(<TestComponent />);
      }).toThrow("useAuth must be used within an AuthProvider");

      consoleSpy.mockRestore();
    });
  });

  describe("initialization", () => {
    it("fetches user on mount", async () => {
      const mockUser = {
        id: "user-1",
        email: "test@example.com",
        name: "Test User",
        role: "user",
        is_active: true,
        must_change_password: false,
        must_change_email: false,
        last_login_at: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      } as Response);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId("loading")).toHaveTextContent("not-loading");
      });

      expect(screen.getByTestId("user")).toHaveTextContent("test@example.com");
      expect(screen.getByTestId("authenticated")).toHaveTextContent("yes");
    });

    it("handles unauthorized response on mount", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
      } as Response);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId("loading")).toHaveTextContent("not-loading");
      });

      expect(screen.getByTestId("user")).toHaveTextContent("no-user");
      expect(screen.getByTestId("authenticated")).toHaveTextContent("no");
    });

    it("handles fetch error on mount", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId("loading")).toHaveTextContent("not-loading");
      });

      expect(screen.getByTestId("user")).toHaveTextContent("no-user");
    });
  });

  describe("login", () => {
    it("successfully logs in and redirects to home", async () => {
      const mockUser = {
        id: "user-1",
        email: "test@example.com",
        name: "Test User",
        role: "user",
        is_active: true,
        must_change_password: false,
        must_change_email: false,
        last_login_at: null,
      };

      // Initial fetch on mount (no user)
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
      } as Response);

      // Login request
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      } as Response);

      const user = userEvent.setup();

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId("loading")).toHaveTextContent("not-loading");
      });

      const loginButton = screen.getByRole("button", { name: "Login" });
      await user.click(loginButton);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining("/api/auth/login"),
          expect.objectContaining({
            method: "POST",
            credentials: "include",
            body: JSON.stringify({ email: "test@example.com", password: "password" }),
          })
        );
      });

      await waitFor(() => {
        expect(screen.getByTestId("user")).toHaveTextContent("test@example.com");
      });

      expect(mockPush).toHaveBeenCalledWith("/");
    });

    it("redirects to setup when user must change password", async () => {
      const mockUser = {
        id: "user-1",
        email: "test@example.com",
        name: "Test User",
        role: "user",
        is_active: true,
        must_change_password: true,
        must_change_email: false,
        last_login_at: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
      } as Response);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      } as Response);

      const user = userEvent.setup();

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId("loading")).toHaveTextContent("not-loading");
      });

      const loginButton = screen.getByRole("button", { name: "Login" });
      await user.click(loginButton);

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/setup");
      });

      expect(screen.getByTestId("requires-setup")).toHaveTextContent("yes");
    });

    it("handles login failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
      } as Response);

      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: "Invalid credentials" }),
      } as Response);

      const user = userEvent.setup();

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId("loading")).toHaveTextContent("not-loading");
      });

      const loginButton = screen.getByRole("button", { name: "Login" });
      await user.click(loginButton);

      await waitFor(() => {
        expect(screen.getByTestId("error")).toHaveTextContent("Invalid credentials");
      });

      expect(screen.getByTestId("user")).toHaveTextContent("no-user");
    });
  });

  describe("logout", () => {
    it("successfully logs out and redirects to login", async () => {
      const mockUser = {
        id: "user-1",
        email: "test@example.com",
        name: "Test User",
        role: "user",
        is_active: true,
        must_change_password: false,
        must_change_email: false,
        last_login_at: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      } as Response);

      mockFetch.mockResolvedValueOnce({
        ok: true,
      } as Response);

      const user = userEvent.setup();

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId("user")).toHaveTextContent("test@example.com");
      });

      const logoutButton = screen.getByRole("button", { name: "Logout" });
      await user.click(logoutButton);

      await waitFor(() => {
        expect(screen.getByTestId("user")).toHaveTextContent("no-user");
      });

      expect(mockPush).toHaveBeenCalledWith("/login");
    });

    it("clears user even if logout request fails", async () => {
      const mockUser = {
        id: "user-1",
        email: "test@example.com",
        name: "Test User",
        role: "user",
        is_active: true,
        must_change_password: false,
        must_change_email: false,
        last_login_at: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      } as Response);

      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const user = userEvent.setup();

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId("user")).toHaveTextContent("test@example.com");
      });

      const logoutButton = screen.getByRole("button", { name: "Logout" });
      await user.click(logoutButton);

      await waitFor(() => {
        expect(screen.getByTestId("user")).toHaveTextContent("no-user");
      });

      expect(mockPush).toHaveBeenCalledWith("/login");
    });
  });

  describe("role checks", () => {
    it("correctly identifies admin role", async () => {
      const mockUser = {
        id: "user-1",
        email: "admin@example.com",
        name: "Admin User",
        role: "admin" as const,
        is_active: true,
        must_change_password: false,
        must_change_email: false,
        last_login_at: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      } as Response);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId("admin")).toHaveTextContent("yes");
      });

      expect(screen.getByTestId("super-admin")).toHaveTextContent("no");
    });

    it("correctly identifies superadmin role", async () => {
      const mockUser = {
        id: "user-1",
        email: "superadmin@example.com",
        name: "Super Admin",
        role: "superadmin" as const,
        is_active: true,
        must_change_password: false,
        must_change_email: false,
        last_login_at: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      } as Response);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId("admin")).toHaveTextContent("yes");
      });

      expect(screen.getByTestId("super-admin")).toHaveTextContent("yes");
    });

    it("correctly identifies regular user", async () => {
      const mockUser = {
        id: "user-1",
        email: "user@example.com",
        name: "Regular User",
        role: "user" as const,
        is_active: true,
        must_change_password: false,
        must_change_email: false,
        last_login_at: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      } as Response);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId("admin")).toHaveTextContent("no");
      });

      expect(screen.getByTestId("super-admin")).toHaveTextContent("no");
    });
  });

  describe("route protection", () => {
    it("redirects to login when unauthenticated on protected route", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
      } as Response);

      (usePathname as jest.Mock).mockReturnValue("/protected");

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/login");
      });
    });

    it("redirects to home when authenticated on login page", async () => {
      const mockUser = {
        id: "user-1",
        email: "test@example.com",
        name: "Test User",
        role: "user",
        is_active: true,
        must_change_password: false,
        must_change_email: false,
        last_login_at: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      } as Response);

      (usePathname as jest.Mock).mockReturnValue("/login");

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/");
      });
    });

    it("redirects to setup when user needs to change password", async () => {
      const mockUser = {
        id: "user-1",
        email: "test@example.com",
        name: "Test User",
        role: "user",
        is_active: true,
        must_change_password: true,
        must_change_email: false,
        last_login_at: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      } as Response);

      (usePathname as jest.Mock).mockReturnValue("/");

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/setup");
      });
    });
  });
});
