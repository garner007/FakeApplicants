import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ApplicantDetailPage from "@/app/applicants/[id]/page";
import * as api from "@/lib/api";
import type { ApplicantDetail } from "@/lib/types";

// Mock the API module
jest.mock("@/lib/api");
const mockApi = api as jest.Mocked<typeof api>;

// Mock useParams to return a test ID
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
  }),
  useParams: () => ({ id: "test-applicant-id" }),
  usePathname: () => "/applicants/test-applicant-id",
  useSearchParams: () => new URLSearchParams(),
}));

const mockApplicant: ApplicantDetail = {
  id: "test-applicant-id",
  lever_id: "abc123-lever-id",
  name: "John Doe",
  email: "john.doe@example.com",
  phone: "+1-555-123-4567",
  location: "San Francisco, CA",
  linkedin_url: "https://linkedin.com/in/johndoe",
  resume_url: "https://lever.co/resumes/abc123.pdf",
  risk_level: "high",
  validation_score: 45.5,
  flag_count: 3,
  is_reviewed: false,
  reviewed_at: null,
  reviewed_by: null,
  created_at: "2024-01-15T10:30:00Z",
  updated_at: "2024-01-15T12:00:00Z",
  flags: [
    {
      id: "flag-1",
      flag_type_code: "VOIP_PHONE",
      flag_type_name: "VoIP Phone Number",
      category: "phone",
      severity: "medium",
      message: "Phone number is registered with Google Voice",
      is_active: true,
      created_at: "2024-01-15T10:35:00Z",
    },
    {
      id: "flag-2",
      flag_type_code: "LINKEDIN_NAME_MISMATCH",
      flag_type_name: "LinkedIn Name Mismatch",
      category: "linkedin",
      severity: "high",
      message: "Name does not match LinkedIn profile",
      is_active: true,
      created_at: "2024-01-15T10:36:00Z",
    },
  ],
};

describe("ApplicantDetailPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("basic rendering", () => {
    it("displays applicant name and email", async () => {
      mockApi.fetchApplicant.mockResolvedValue(mockApplicant);

      render(<ApplicantDetailPage />);

      await waitFor(() => {
        expect(screen.getByText("John Doe")).toBeInTheDocument();
      });
      // Email appears in header and contact info, so check for at least one
      expect(screen.getAllByText("john.doe@example.com").length).toBeGreaterThanOrEqual(1);
    });

    it("displays risk level badge", async () => {
      mockApi.fetchApplicant.mockResolvedValue(mockApplicant);

      render(<ApplicantDetailPage />);

      await waitFor(() => {
        expect(screen.getByText("HIGH RISK")).toBeInTheDocument();
      });
    });

    it("displays validation score", async () => {
      mockApi.fetchApplicant.mockResolvedValue(mockApplicant);

      render(<ApplicantDetailPage />);

      await waitFor(() => {
        expect(screen.getByText("45.5%")).toBeInTheDocument();
      });
    });

    it("displays all active flags", async () => {
      mockApi.fetchApplicant.mockResolvedValue(mockApplicant);

      render(<ApplicantDetailPage />);

      await waitFor(() => {
        expect(screen.getByText("VoIP Phone Number")).toBeInTheDocument();
      });
      expect(screen.getByText("LinkedIn Name Mismatch")).toBeInTheDocument();
      expect(screen.getByText("Phone number is registered with Google Voice")).toBeInTheDocument();
    });
  });

  describe("external links", () => {
    it("displays LinkedIn profile link when available", async () => {
      mockApi.fetchApplicant.mockResolvedValue(mockApplicant);

      render(<ApplicantDetailPage />);

      await waitFor(() => {
        const linkedinLink = screen.getByRole("link", { name: /view profile/i });
        expect(linkedinLink).toHaveAttribute("href", "https://linkedin.com/in/johndoe");
        expect(linkedinLink).toHaveAttribute("target", "_blank");
      });
    });

    it("displays Lever profile link", async () => {
      mockApi.fetchApplicant.mockResolvedValue(mockApplicant);

      render(<ApplicantDetailPage />);

      await waitFor(() => {
        const leverLink = screen.getByRole("link", { name: /view in lever/i });
        expect(leverLink).toHaveAttribute("href", expect.stringContaining("abc123-lever-id"));
        expect(leverLink).toHaveAttribute("target", "_blank");
      });
    });

    it("displays resume link when available", async () => {
      mockApi.fetchApplicant.mockResolvedValue(mockApplicant);

      render(<ApplicantDetailPage />);

      await waitFor(() => {
        const resumeLink = screen.getByRole("link", { name: /view resume/i });
        expect(resumeLink).toHaveAttribute("href", "https://lever.co/resumes/abc123.pdf");
        expect(resumeLink).toHaveAttribute("target", "_blank");
      });
    });

    it("does not display resume link when not available", async () => {
      mockApi.fetchApplicant.mockResolvedValue({
        ...mockApplicant,
        resume_url: null,
      });

      render(<ApplicantDetailPage />);

      await waitFor(() => {
        expect(screen.getByText("John Doe")).toBeInTheDocument();
      });
      expect(screen.queryByRole("link", { name: /view resume/i })).not.toBeInTheDocument();
    });
  });

  describe("review functionality", () => {
    it("displays unchecked reviewed checkbox when not reviewed", async () => {
      mockApi.fetchApplicant.mockResolvedValue(mockApplicant);

      render(<ApplicantDetailPage />);

      await waitFor(() => {
        const checkbox = screen.getByRole("checkbox", { name: /mark as reviewed/i });
        expect(checkbox).not.toBeChecked();
      });
    });

    it("displays checked reviewed checkbox when reviewed", async () => {
      mockApi.fetchApplicant.mockResolvedValue({
        ...mockApplicant,
        is_reviewed: true,
        reviewed_at: "2024-01-16T14:00:00Z",
        reviewed_by: "Jane Smith",
      });

      render(<ApplicantDetailPage />);

      await waitFor(() => {
        const checkbox = screen.getByRole("checkbox", { name: /mark as reviewed/i });
        expect(checkbox).toBeChecked();
      });
      expect(screen.getByText(/jane smith/i)).toBeInTheDocument();
    });

    it("calls updateApplicantReviewed when checkbox is clicked", async () => {
      const user = userEvent.setup();
      mockApi.fetchApplicant.mockResolvedValue(mockApplicant);
      mockApi.updateApplicantReviewed.mockResolvedValue({
        ...mockApplicant,
        is_reviewed: true,
        reviewed_at: "2024-01-16T14:00:00Z",
      });

      render(<ApplicantDetailPage />);

      await waitFor(() => {
        expect(screen.getByText("John Doe")).toBeInTheDocument();
      });

      const checkbox = screen.getByRole("checkbox", { name: /mark as reviewed/i });
      await user.click(checkbox);

      expect(mockApi.updateApplicantReviewed).toHaveBeenCalledWith(
        "test-applicant-id",
        true
      );
    });
  });

  describe("error handling", () => {
    it("displays error message when fetch fails", async () => {
      mockApi.fetchApplicant.mockRejectedValue(new Error("Network error"));

      render(<ApplicantDetailPage />);

      await waitFor(() => {
        expect(screen.getByText("Network error")).toBeInTheDocument();
      });
    });

    it("displays not found message for 404", async () => {
      mockApi.fetchApplicant.mockRejectedValue(new Error("Applicant not found"));

      render(<ApplicantDetailPage />);

      await waitFor(() => {
        expect(screen.getByText("Applicant not found")).toBeInTheDocument();
      });
    });
  });

  describe("loading state", () => {
    it("displays loading message initially", () => {
      mockApi.fetchApplicant.mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      render(<ApplicantDetailPage />);

      expect(screen.getByText(/loading applicant/i)).toBeInTheDocument();
    });
  });
});
