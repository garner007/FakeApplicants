import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Header } from "@/components/header";
import { useAuth } from "@/lib/auth-context";
import { usePathname } from "next/navigation";
import type { User } from "@/lib/auth-context";

// Mock the auth context
jest.mock("@/lib/auth-context");
const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

// Mock next/navigation
jest.mock("next/navigation", () => ({
  ...jest.requireActual("next/navigation"),
  usePathname: jest.fn(),
}));

describe("Header", () => {
  const mockUser: User = {
    id: "user-1",
    email: "test@example.com",
    name: "Test User",
    role: "user",
    is_active: true,
    must_change_password: false,
    must_change_email: false,
    last_login_at: null,
  };

  const mockLogout = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (usePathname as jest.Mock).mockReturnValue("/");
  });

  describe("branding and logo", () => {
    it("renders app title and logo", () => {
      mockUseAuth.mockReturnValue({
        user: mockUser,
        loading: false,
        error: null,
        login: jest.fn(),
        logout: mockLogout,
        changePassword: jest.fn(),
        initialSetup: jest.fn(),
        refreshUser: jest.fn(),
        isAuthenticated: true,
        isAdmin: false,
        isSuperAdmin: false,
        mustChangePassword: false,
        mustChangeEmail: false,
        requiresSetup: false,
      });

      render(<Header />);

      expect(screen.getByText("Applicant Validator")).toBeInTheDocument();
    });

    it("logo links to home page", () => {
      mockUseAuth.mockReturnValue({
        user: mockUser,
        loading: false,
        error: null,
        login: jest.fn(),
        logout: mockLogout,
        changePassword: jest.fn(),
        initialSetup: jest.fn(),
        refreshUser: jest.fn(),
        isAuthenticated: true,
        isAdmin: false,
        isSuperAdmin: false,
        mustChangePassword: false,
        mustChangeEmail: false,
        requiresSetup: false,
      });

      render(<Header />);

      const logoLink = screen.getByText("Applicant Validator").closest("a");
      expect(logoLink).toHaveAttribute("href", "/");
    });
  });

  describe("navigation links for regular users", () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: mockUser,
        loading: false,
        error: null,
        login: jest.fn(),
        logout: mockLogout,
        changePassword: jest.fn(),
        initialSetup: jest.fn(),
        refreshUser: jest.fn(),
        isAuthenticated: true,
        isAdmin: false,
        isSuperAdmin: false,
        mustChangePassword: false,
        mustChangeEmail: false,
        requiresSetup: false,
      });
    });

    it("displays Applicants and Validation Rules links", () => {
      render(<Header />);

      expect(screen.getByRole("link", { name: "Applicants" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Validation Rules" })).toBeInTheDocument();
    });

    it("does not display admin-only links", () => {
      render(<Header />);

      expect(screen.queryByRole("link", { name: "Integrations" })).not.toBeInTheDocument();
      expect(screen.queryByRole("link", { name: "Admin" })).not.toBeInTheDocument();
    });

    it("highlights active navigation link", () => {
      (usePathname as jest.Mock).mockReturnValue("/");
      render(<Header />);

      const applicantsLink = screen.getByRole("link", { name: "Applicants" });
      expect(applicantsLink).toHaveClass("bg-gray-900");
    });
  });

  describe("navigation links for admins", () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { ...mockUser, role: "admin" },
        loading: false,
        error: null,
        login: jest.fn(),
        logout: mockLogout,
        changePassword: jest.fn(),
        initialSetup: jest.fn(),
        refreshUser: jest.fn(),
        isAuthenticated: true,
        isAdmin: true,
        isSuperAdmin: false,
        mustChangePassword: false,
        mustChangeEmail: false,
        requiresSetup: false,
      });
    });

    it("displays admin-only links", () => {
      render(<Header />);

      expect(screen.getByRole("link", { name: "Integrations" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Validation Data/ })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Admin" })).toBeInTheDocument();
    });

    it("opens Validation Data dropdown on click", async () => {
      const user = userEvent.setup();
      render(<Header />);

      const validationDataButton = screen.getByRole("button", { name: /Validation Data/ });
      await user.click(validationDataButton);

      await waitFor(() => {
        expect(screen.getByRole("link", { name: "Disposable Domains" })).toBeInTheDocument();
        expect(screen.getByRole("link", { name: "VoIP Carriers" })).toBeInTheDocument();
      });
    });

    it("highlights Validation Data dropdown when on validation data page", () => {
      (usePathname as jest.Mock).mockReturnValue("/validation-data/disposable-domains");
      render(<Header />);

      const validationDataButton = screen.getByRole("button", { name: /Validation Data/ });
      expect(validationDataButton).toHaveClass("bg-gray-900");
    });
  });

  describe("user menu - not logged in", () => {
    it("displays Sign In button when not authenticated", () => {
      mockUseAuth.mockReturnValue({
        user: null,
        loading: false,
        error: null,
        login: jest.fn(),
        logout: mockLogout,
        changePassword: jest.fn(),
        initialSetup: jest.fn(),
        refreshUser: jest.fn(),
        isAuthenticated: false,
        isAdmin: false,
        isSuperAdmin: false,
        mustChangePassword: false,
        mustChangeEmail: false,
        requiresSetup: false,
      });

      render(<Header />);

      expect(screen.getByRole("link", { name: "Sign In" })).toBeInTheDocument();
    });

    it("Sign In button links to login page", () => {
      mockUseAuth.mockReturnValue({
        user: null,
        loading: false,
        error: null,
        login: jest.fn(),
        logout: mockLogout,
        changePassword: jest.fn(),
        initialSetup: jest.fn(),
        refreshUser: jest.fn(),
        isAuthenticated: false,
        isAdmin: false,
        isSuperAdmin: false,
        mustChangePassword: false,
        mustChangeEmail: false,
        requiresSetup: false,
      });

      render(<Header />);

      const signInLink = screen.getByRole("link", { name: "Sign In" });
      expect(signInLink).toHaveAttribute("href", "/login");
    });
  });

  describe("user menu - logged in", () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: mockUser,
        loading: false,
        error: null,
        login: jest.fn(),
        logout: mockLogout,
        changePassword: jest.fn(),
        initialSetup: jest.fn(),
        refreshUser: jest.fn(),
        isAuthenticated: true,
        isAdmin: false,
        isSuperAdmin: false,
        mustChangePassword: false,
        mustChangeEmail: false,
        requiresSetup: false,
      });
    });

    it("displays user name initial in avatar", () => {
      render(<Header />);

      expect(screen.getByText("T")).toBeInTheDocument(); // "T" from "Test User"
    });

    it("displays user name in menu trigger", () => {
      render(<Header />);

      expect(screen.getByText("Test User")).toBeInTheDocument();
    });

    it("opens user menu on click", async () => {
      const user = userEvent.setup();
      render(<Header />);

      const userButton = screen.getByText("Test User").closest("button");
      await user.click(userButton!);

      await waitFor(() => {
        expect(screen.getByText("test@example.com")).toBeInTheDocument();
        expect(screen.getByRole("link", { name: "Change Password" })).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Sign Out" })).toBeInTheDocument();
      });
    });

    it("displays user role badge", async () => {
      const user = userEvent.setup();
      render(<Header />);

      const userButton = screen.getByText("Test User").closest("button");
      await user.click(userButton!);

      await waitFor(() => {
        expect(screen.getByText("user")).toBeInTheDocument();
      });
    });

    it("calls logout when Sign Out is clicked", async () => {
      const user = userEvent.setup();
      render(<Header />);

      const userButton = screen.getByText("Test User").closest("button");
      await user.click(userButton!);

      await waitFor(() => {
        expect(screen.getByRole("button", { name: "Sign Out" })).toBeInTheDocument();
      });

      const signOutButton = screen.getByRole("button", { name: "Sign Out" });
      await user.click(signOutButton);

      expect(mockLogout).toHaveBeenCalled();
    });
  });

  describe("user menu - admin", () => {
    it("displays Manage Users link for admins", async () => {
      mockUseAuth.mockReturnValue({
        user: { ...mockUser, role: "admin" },
        loading: false,
        error: null,
        login: jest.fn(),
        logout: mockLogout,
        changePassword: jest.fn(),
        initialSetup: jest.fn(),
        refreshUser: jest.fn(),
        isAuthenticated: true,
        isAdmin: true,
        isSuperAdmin: false,
        mustChangePassword: false,
        mustChangeEmail: false,
        requiresSetup: false,
      });

      const user = userEvent.setup();
      render(<Header />);

      const userButton = screen.getByText("Test User").closest("button");
      await user.click(userButton!);

      await waitFor(() => {
        expect(screen.getByRole("link", { name: "Manage Users" })).toBeInTheDocument();
      });
    });

    it("does not display Manage Users for regular users", async () => {
      mockUseAuth.mockReturnValue({
        user: mockUser,
        loading: false,
        error: null,
        login: jest.fn(),
        logout: mockLogout,
        changePassword: jest.fn(),
        initialSetup: jest.fn(),
        refreshUser: jest.fn(),
        isAuthenticated: true,
        isAdmin: false,
        isSuperAdmin: false,
        mustChangePassword: false,
        mustChangeEmail: false,
        requiresSetup: false,
      });

      const user = userEvent.setup();
      render(<Header />);

      const userButton = screen.getByText("Test User").closest("button");
      await user.click(userButton!);

      await waitFor(() => {
        expect(screen.getByRole("button", { name: "Sign Out" })).toBeInTheDocument();
      });

      expect(screen.queryByRole("link", { name: "Manage Users" })).not.toBeInTheDocument();
    });
  });

  describe("role badge colors", () => {
    it("displays purple badge for superadmin", async () => {
      mockUseAuth.mockReturnValue({
        user: { ...mockUser, role: "superadmin" },
        loading: false,
        error: null,
        login: jest.fn(),
        logout: mockLogout,
        changePassword: jest.fn(),
        initialSetup: jest.fn(),
        refreshUser: jest.fn(),
        isAuthenticated: true,
        isAdmin: true,
        isSuperAdmin: true,
        mustChangePassword: false,
        mustChangeEmail: false,
        requiresSetup: false,
      });

      const user = userEvent.setup();
      render(<Header />);

      const userButton = screen.getByText("Test User").closest("button");
      await user.click(userButton!);

      await waitFor(() => {
        const badge = screen.getByText("superadmin");
        expect(badge.className).toContain("bg-purple-100");
      });
    });

    it("displays blue badge for admin", async () => {
      mockUseAuth.mockReturnValue({
        user: { ...mockUser, role: "admin" },
        loading: false,
        error: null,
        login: jest.fn(),
        logout: mockLogout,
        changePassword: jest.fn(),
        initialSetup: jest.fn(),
        refreshUser: jest.fn(),
        isAuthenticated: true,
        isAdmin: true,
        isSuperAdmin: false,
        mustChangePassword: false,
        mustChangeEmail: false,
        requiresSetup: false,
      });

      const user = userEvent.setup();
      render(<Header />);

      const userButton = screen.getByText("Test User").closest("button");
      await user.click(userButton!);

      await waitFor(() => {
        const badge = screen.getByText("admin");
        expect(badge.className).toContain("bg-blue-100");
      });
    });

    it("displays green badge for regular user", async () => {
      const user = userEvent.setup();
      render(<Header />);

      const userButton = screen.getByText("Test User").closest("button");
      await user.click(userButton!);

      await waitFor(() => {
        const badge = screen.getByText("user");
        expect(badge.className).toContain("bg-green-100");
      });
    });
  });

  describe("mobile menu", () => {
    it("displays mobile menu button", () => {
      mockUseAuth.mockReturnValue({
        user: mockUser,
        loading: false,
        error: null,
        login: jest.fn(),
        logout: mockLogout,
        changePassword: jest.fn(),
        initialSetup: jest.fn(),
        refreshUser: jest.fn(),
        isAuthenticated: true,
        isAdmin: false,
        isSuperAdmin: false,
        mustChangePassword: false,
        mustChangeEmail: false,
        requiresSetup: false,
      });

      render(<Header />);

      const mobileMenuButton = screen.getByRole("button", { name: "Toggle menu" });
      expect(mobileMenuButton).toBeInTheDocument();
    });

    it("opens mobile menu on click", async () => {
      mockUseAuth.mockReturnValue({
        user: mockUser,
        loading: false,
        error: null,
        login: jest.fn(),
        logout: mockLogout,
        changePassword: jest.fn(),
        initialSetup: jest.fn(),
        refreshUser: jest.fn(),
        isAuthenticated: true,
        isAdmin: false,
        isSuperAdmin: false,
        mustChangePassword: false,
        mustChangeEmail: false,
        requiresSetup: false,
      });

      const user = userEvent.setup();
      render(<Header />);

      const mobileMenuButton = screen.getByRole("button", { name: "Toggle menu" });
      await user.click(mobileMenuButton);

      // The mobile menu has duplicate links (desktop + mobile), so we check for presence
      const applicantsLinks = screen.getAllByRole("link", { name: "Applicants" });
      expect(applicantsLinks.length).toBeGreaterThan(1); // At least desktop + mobile
    });

    it("displays admin links in mobile menu for admins", async () => {
      mockUseAuth.mockReturnValue({
        user: { ...mockUser, role: "admin" },
        loading: false,
        error: null,
        login: jest.fn(),
        logout: mockLogout,
        changePassword: jest.fn(),
        initialSetup: jest.fn(),
        refreshUser: jest.fn(),
        isAuthenticated: true,
        isAdmin: true,
        isSuperAdmin: false,
        mustChangePassword: false,
        mustChangeEmail: false,
        requiresSetup: false,
      });

      const user = userEvent.setup();
      render(<Header />);

      const mobileMenuButton = screen.getByRole("button", { name: "Toggle menu" });
      await user.click(mobileMenuButton);

      await waitFor(() => {
        const adminLinks = screen.getAllByRole("link", { name: "Admin" });
        expect(adminLinks.length).toBeGreaterThan(0);
      });
    });
  });

  describe("accessibility", () => {
    it("has proper ARIA attributes for dropdowns", () => {
      mockUseAuth.mockReturnValue({
        user: { ...mockUser, role: "admin" },
        loading: false,
        error: null,
        login: jest.fn(),
        logout: mockLogout,
        changePassword: jest.fn(),
        initialSetup: jest.fn(),
        refreshUser: jest.fn(),
        isAuthenticated: true,
        isAdmin: true,
        isSuperAdmin: false,
        mustChangePassword: false,
        mustChangeEmail: false,
        requiresSetup: false,
      });

      render(<Header />);

      const validationDataButton = screen.getByRole("button", { name: /Validation Data/ });
      expect(validationDataButton).toHaveAttribute("aria-expanded");
      expect(validationDataButton).toHaveAttribute("aria-haspopup", "true");
    });

    it("has accessible mobile menu button", () => {
      mockUseAuth.mockReturnValue({
        user: mockUser,
        loading: false,
        error: null,
        login: jest.fn(),
        logout: mockLogout,
        changePassword: jest.fn(),
        initialSetup: jest.fn(),
        refreshUser: jest.fn(),
        isAuthenticated: true,
        isAdmin: false,
        isSuperAdmin: false,
        mustChangePassword: false,
        mustChangeEmail: false,
        requiresSetup: false,
      });

      render(<Header />);

      const mobileMenuButton = screen.getByRole("button", { name: "Toggle menu" });
      expect(mobileMenuButton).toHaveAttribute("aria-label", "Toggle menu");
    });
  });
});
