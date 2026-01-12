import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LoginPage from "@/app/login/page";
import { useAuth } from "@/lib/auth-context";

// Mock the auth context
jest.mock("@/lib/auth-context");
const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

describe("LoginPage", () => {
  const mockLogin = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuth.mockReturnValue({
      user: null,
      loading: false,
      error: null,
      login: mockLogin,
      logout: jest.fn(),
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
  });

  describe("rendering", () => {
    it("renders login form with all fields", () => {
      render(<LoginPage />);

      expect(screen.getByText("Applicant Validator")).toBeInTheDocument();
      expect(screen.getByText("Sign in to access the application")).toBeInTheDocument();
      expect(screen.getByLabelText("Email")).toBeInTheDocument();
      expect(screen.getByLabelText("Password")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Sign In" })).toBeInTheDocument();
    });

    it("renders email input with correct attributes", () => {
      render(<LoginPage />);

      const emailInput = screen.getByLabelText("Email");
      expect(emailInput).toHaveAttribute("type", "email");
      expect(emailInput).toHaveAttribute("placeholder", "you@company.com");
      expect(emailInput).toHaveAttribute("required");
      expect(emailInput).toHaveAttribute("autocomplete", "email");
    });

    it("renders password input with correct attributes", () => {
      render(<LoginPage />);

      const passwordInput = screen.getByLabelText("Password");
      expect(passwordInput).toHaveAttribute("type", "password");
      expect(passwordInput).toHaveAttribute("placeholder", "Enter your password");
      expect(passwordInput).toHaveAttribute("required");
      expect(passwordInput).toHaveAttribute("autocomplete", "current-password");
    });
  });

  describe("form validation", () => {
    it("disables submit button when email is empty", () => {
      render(<LoginPage />);

      const submitButton = screen.getByRole("button", { name: "Sign In" });
      expect(submitButton).toBeDisabled();
    });

    it("enables submit button when both fields are filled", async () => {
      const user = userEvent.setup();
      render(<LoginPage />);

      const emailInput = screen.getByLabelText("Email");
      const passwordInput = screen.getByLabelText("Password");
      const submitButton = screen.getByRole("button", { name: "Sign In" });

      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "password123");

      expect(submitButton).toBeEnabled();
    });
  });

  describe("form submission", () => {
    it("calls login with email and password on submit", async () => {
      mockLogin.mockResolvedValueOnce(undefined);
      const user = userEvent.setup();

      render(<LoginPage />);

      const emailInput = screen.getByLabelText("Email");
      const passwordInput = screen.getByLabelText("Password");
      const submitButton = screen.getByRole("button", { name: "Sign In" });

      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "password123");
      await user.click(submitButton);

      expect(mockLogin).toHaveBeenCalledWith("test@example.com", "password123");
    });

    it("displays loading state during login", async () => {
      let resolveLogin: () => void;
      mockLogin.mockReturnValueOnce(
        new Promise<void>((resolve) => {
          resolveLogin = resolve;
        })
      );

      const user = userEvent.setup();
      render(<LoginPage />);

      const emailInput = screen.getByLabelText("Email");
      const passwordInput = screen.getByLabelText("Password");
      const submitButton = screen.getByRole("button", { name: "Sign In" });

      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "password123");
      await user.click(submitButton);

      expect(screen.getByRole("button", { name: "Signing in..." })).toBeInTheDocument();
      expect(submitButton).toBeDisabled();

      resolveLogin!();
      await waitFor(() => {
        expect(screen.queryByRole("button", { name: "Signing in..." })).not.toBeInTheDocument();
      });
    });

    it("disables inputs during loading", async () => {
      let resolveLogin: () => void;
      mockLogin.mockReturnValueOnce(
        new Promise<void>((resolve) => {
          resolveLogin = resolve;
        })
      );

      const user = userEvent.setup();
      render(<LoginPage />);

      const emailInput = screen.getByLabelText("Email");
      const passwordInput = screen.getByLabelText("Password");

      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "password123");
      await user.click(screen.getByRole("button", { name: "Sign In" }));

      expect(emailInput).toBeDisabled();
      expect(passwordInput).toBeDisabled();

      resolveLogin!();
      await waitFor(() => {
        expect(emailInput).not.toBeDisabled();
      });
    });

    it("prevents form submission when already loading", async () => {
      mockLogin.mockResolvedValueOnce(undefined);
      const user = userEvent.setup();

      render(<LoginPage />);

      const emailInput = screen.getByLabelText("Email");
      const passwordInput = screen.getByLabelText("Password");
      const submitButton = screen.getByRole("button");

      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "password123");
      await user.click(submitButton);

      // Try to click again while loading
      expect(submitButton).toBeDisabled();
    });
  });

  describe("error handling", () => {
    it("displays error message on login failure", async () => {
      mockLogin.mockRejectedValueOnce(new Error("Invalid credentials"));
      const user = userEvent.setup();

      render(<LoginPage />);

      const emailInput = screen.getByLabelText("Email");
      const passwordInput = screen.getByLabelText("Password");
      const submitButton = screen.getByRole("button", { name: "Sign In" });

      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "wrongpassword");
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
      });
    });

    it("clears error message on new submission", async () => {
      mockLogin
        .mockRejectedValueOnce(new Error("Invalid credentials"))
        .mockResolvedValueOnce(undefined);

      const user = userEvent.setup();
      render(<LoginPage />);

      const emailInput = screen.getByLabelText("Email");
      const passwordInput = screen.getByLabelText("Password");
      const submitButton = screen.getByRole("button", { name: "Sign In" });

      // First attempt - fails
      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "wrongpassword");
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
      });

      // Second attempt - clears error
      await user.clear(passwordInput);
      await user.type(passwordInput, "correctpassword");
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.queryByText("Invalid credentials")).not.toBeInTheDocument();
      });
    });

    it("handles non-Error exceptions", async () => {
      mockLogin.mockRejectedValueOnce("String error");
      const user = userEvent.setup();

      render(<LoginPage />);

      const emailInput = screen.getByLabelText("Email");
      const passwordInput = screen.getByLabelText("Password");

      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "password123");
      await user.click(screen.getByRole("button", { name: "Sign In" }));

      await waitFor(() => {
        expect(screen.getByText("Login failed")).toBeInTheDocument();
      });
    });
  });

  describe("accessibility", () => {
    it("associates labels with inputs", () => {
      render(<LoginPage />);

      const emailInput = screen.getByLabelText("Email");
      const passwordInput = screen.getByLabelText("Password");

      expect(emailInput).toHaveAttribute("id", "email");
      expect(passwordInput).toHaveAttribute("id", "password");
    });

    it("displays error with proper styling", async () => {
      mockLogin.mockRejectedValueOnce(new Error("Test error"));
      const user = userEvent.setup();

      render(<LoginPage />);

      await user.type(screen.getByLabelText("Email"), "test@example.com");
      await user.type(screen.getByLabelText("Password"), "password");
      await user.click(screen.getByRole("button", { name: "Sign In" }));

      await waitFor(() => {
        const errorDiv = screen.getByText("Test error");
        expect(errorDiv).toBeInTheDocument();
        expect(errorDiv.className).toContain("text-red-500");
      });
    });
  });

  describe("keyboard navigation", () => {
    it("allows form submission via Enter key", async () => {
      mockLogin.mockResolvedValueOnce(undefined);
      const user = userEvent.setup();

      render(<LoginPage />);

      const emailInput = screen.getByLabelText("Email");
      const passwordInput = screen.getByLabelText("Password");

      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "password123");
      await user.keyboard("{Enter}");

      expect(mockLogin).toHaveBeenCalledWith("test@example.com", "password123");
    });

    it("allows tabbing between fields", async () => {
      const user = userEvent.setup();
      render(<LoginPage />);

      const emailInput = screen.getByLabelText("Email");
      const passwordInput = screen.getByLabelText("Password");

      await user.click(emailInput);
      await user.keyboard("{Tab}");

      expect(passwordInput).toHaveFocus();
    });
  });

  describe("input behavior", () => {
    it("updates email value as user types", async () => {
      const user = userEvent.setup();
      render(<LoginPage />);

      const emailInput = screen.getByLabelText("Email") as HTMLInputElement;
      await user.type(emailInput, "test@example.com");

      expect(emailInput.value).toBe("test@example.com");
    });

    it("updates password value as user types", async () => {
      const user = userEvent.setup();
      render(<LoginPage />);

      const passwordInput = screen.getByLabelText("Password") as HTMLInputElement;
      await user.type(passwordInput, "secret123");

      expect(passwordInput.value).toBe("secret123");
    });

    it("masks password input", () => {
      render(<LoginPage />);

      const passwordInput = screen.getByLabelText("Password");
      expect(passwordInput).toHaveAttribute("type", "password");
    });
  });
});
