import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Home from "@/app/page";
import * as api from "@/lib/api";
import type { PaginatedApplicantsResponse, Applicant } from "@/lib/types";

// Mock the API module
jest.mock("@/lib/api");
const mockApi = api as jest.Mocked<typeof api>;

// Mock child components
jest.mock("@/components/header", () => ({
  Header: () => <div data-testid="mock-header">Header</div>,
}));

jest.mock("@/components/applicants-table", () => ({
  ApplicantsTable: ({ applicants, onSort }: any) => (
    <div data-testid="mock-table">
      <div data-testid="applicant-count">{applicants.length}</div>
      <button onClick={() => onSort("name")}>Sort by Name</button>
    </div>
  ),
}));

jest.mock("@/components/sync-panel", () => ({
  SyncPanel: ({ onSyncComplete }: any) => (
    <div data-testid="mock-sync-panel">
      <button onClick={onSyncComplete}>Complete Sync</button>
    </div>
  ),
}));

jest.mock("@/components/revalidate-panel", () => ({
  RevalidateFilterPanel: ({ onRevalidateComplete }: any) => (
    <div data-testid="mock-revalidate-panel">
      <button onClick={onRevalidateComplete}>Complete Revalidate</button>
    </div>
  ),
}));

const mockApplicants: Applicant[] = [
  {
    id: "1",
    lever_id: "lever-1",
    name: "John Doe",
    email: "john@example.com",
    phone: "+1-555-1234",
    location: "New York",
    risk_level: "low",
    flag_count: 0,
    opportunity_count: 1,
    is_reviewed: false,
    reviewed_at: null,
    created_at: "2024-01-15T10:00:00Z",
    lever_created_at: "2024-01-15T09:00:00Z",
    flags: [],
    sources: ["LinkedIn"],
    assigned_ta: "TA 1",
  },
  {
    id: "2",
    lever_id: "lever-2",
    name: "Jane Smith",
    email: "jane@example.com",
    phone: null,
    location: "San Francisco",
    risk_level: "high",
    flag_count: 3,
    opportunity_count: 2,
    is_reviewed: false,
    reviewed_at: null,
    created_at: "2024-01-16T10:00:00Z",
    lever_created_at: "2024-01-16T09:00:00Z",
    flags: [],
    sources: ["Indeed"],
    assigned_ta: "TA 2",
  },
];

describe("Home Page", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("initial rendering", () => {
    it("renders page header and description", async () => {
      const mockResponse: PaginatedApplicantsResponse = {
        items: mockApplicants,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      };

      mockApi.fetchApplicants.mockResolvedValue(mockResponse);
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      render(<Home />);

      expect(screen.getByText("Applicants")).toBeInTheDocument();
      expect(
        screen.getByText("Review and validate job applicants for potential fraud indicators.")
      ).toBeInTheDocument();
    });

    it("renders header component", async () => {
      mockApi.fetchApplicants.mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      });
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      render(<Home />);

      await waitFor(() => {
        expect(screen.getByTestId("mock-header")).toBeInTheDocument();
      });
    });

    it("renders sync and revalidate panels", async () => {
      mockApi.fetchApplicants.mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      });
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      render(<Home />);

      await waitFor(() => {
        expect(screen.getByTestId("mock-sync-panel")).toBeInTheDocument();
        expect(screen.getByTestId("mock-revalidate-panel")).toBeInTheDocument();
      });
    });
  });

  describe("loading state", () => {
    it("displays loading message initially", () => {
      mockApi.fetchApplicants.mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      render(<Home />);

      expect(screen.getByText("Loading applicants...")).toBeInTheDocument();
    });

    it("displays Loading... in count area during fetch", () => {
      mockApi.fetchApplicants.mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      render(<Home />);

      expect(screen.getByText("Loading...")).toBeInTheDocument();
    });
  });

  describe("data fetching", () => {
    it("fetches and displays applicants", async () => {
      const mockResponse: PaginatedApplicantsResponse = {
        items: mockApplicants,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      };

      mockApi.fetchApplicants.mockResolvedValue(mockResponse);
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      render(<Home />);

      await waitFor(() => {
        expect(screen.getByText("2 applicants found")).toBeInTheDocument();
      });

      expect(screen.getByTestId("mock-table")).toBeInTheDocument();
      expect(screen.getByTestId("applicant-count")).toHaveTextContent("2");
    });

    it("fetches filter options on mount", async () => {
      mockApi.fetchApplicants.mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      });
      mockApi.getTAs.mockResolvedValue(["TA 1", "TA 2"]);
      mockApi.getSources.mockResolvedValue(["LinkedIn", "Indeed"]);
      mockApi.getRiskLevels.mockResolvedValue(["low", "medium", "high"]);
      mockApi.getFlagTypes.mockResolvedValue([
        { code: "VOIP_PHONE", name: "VoIP Phone", category: "phone" },
      ]);

      render(<Home />);

      await waitFor(() => {
        expect(mockApi.getTAs).toHaveBeenCalled();
        expect(mockApi.getSources).toHaveBeenCalled();
        expect(mockApi.getRiskLevels).toHaveBeenCalled();
        expect(mockApi.getFlagTypes).toHaveBeenCalled();
      });
    });

    it("handles fetch error gracefully", async () => {
      mockApi.fetchApplicants.mockRejectedValue(new Error("Network error"));
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      render(<Home />);

      await waitFor(() => {
        expect(screen.getByText("Network error")).toBeInTheDocument();
      });
    });
  });

  describe("error handling", () => {
    it("displays error message and retry button on failure", async () => {
      mockApi.fetchApplicants.mockRejectedValue(new Error("Failed to load"));
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      render(<Home />);

      await waitFor(() => {
        expect(screen.getByText("Failed to load")).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
      });
    });

    it("retries loading when retry button is clicked", async () => {
      mockApi.fetchApplicants
        .mockRejectedValueOnce(new Error("Failed to load"))
        .mockResolvedValueOnce({
          items: mockApplicants,
          total: 2,
          page: 1,
          page_size: 20,
          total_pages: 1,
        });
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      const user = userEvent.setup();
      render(<Home />);

      await waitFor(() => {
        expect(screen.getByText("Failed to load")).toBeInTheDocument();
      });

      const retryButton = screen.getByRole("button", { name: "Retry" });
      await user.click(retryButton);

      await waitFor(() => {
        expect(screen.getByText("2 applicants found")).toBeInTheDocument();
      });
    });
  });

  describe("filtering", () => {
    it("applies TA filter", async () => {
      mockApi.fetchApplicants.mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      });
      mockApi.getTAs.mockResolvedValue(["John Smith", "Jane Doe"]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      const user = userEvent.setup();
      render(<Home />);

      await waitFor(() => {
        expect(screen.getByText("TA:")).toBeInTheDocument();
      });

      // Find and click the TA select trigger
      const taSelect = screen.getByRole("combobox", { name: /All TAs/i });
      await user.click(taSelect);

      // Select a TA
      const taOption = screen.getByRole("option", { name: "John Smith" });
      await user.click(taOption);

      await waitFor(() => {
        expect(mockApi.fetchApplicants).toHaveBeenCalledWith(
          expect.objectContaining({
            assignedTa: "John Smith",
            page: 1,
          })
        );
      });
    });

    it("applies risk level filter", async () => {
      mockApi.fetchApplicants.mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      });
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue(["low", "medium", "high"]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      const user = userEvent.setup();
      render(<Home />);

      await waitFor(() => {
        expect(screen.getByText("Risk Level:")).toBeInTheDocument();
      });

      const riskSelect = screen.getByRole("combobox", { name: /All Levels/i });
      await user.click(riskSelect);

      const highOption = screen.getByRole("option", { name: "High" });
      await user.click(highOption);

      await waitFor(() => {
        expect(mockApi.fetchApplicants).toHaveBeenCalledWith(
          expect.objectContaining({
            riskLevel: "high",
            page: 1,
          })
        );
      });
    });

    it("resets page to 1 when filter changes", async () => {
      mockApi.fetchApplicants.mockResolvedValue({
        items: mockApplicants,
        total: 50,
        page: 1,
        page_size: 20,
        total_pages: 3,
      });
      mockApi.getTAs.mockResolvedValue(["TA 1"]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      const user = userEvent.setup();
      render(<Home />);

      await waitFor(() => {
        expect(screen.getByText("50 applicants found")).toBeInTheDocument();
      });

      // Go to page 2
      const nextButton = screen.getByRole("button", { name: "Next" });
      await user.click(nextButton);

      // Change filter - should reset to page 1
      const taSelect = screen.getByRole("combobox", { name: /All TAs/i });
      await user.click(taSelect);
      const taOption = screen.getByRole("option", { name: "TA 1" });
      await user.click(taOption);

      await waitFor(() => {
        expect(mockApi.fetchApplicants).toHaveBeenLastCalledWith(
          expect.objectContaining({
            page: 1,
          })
        );
      });
    });
  });

  describe("sorting", () => {
    it("changes sort order when clicking same field", async () => {
      mockApi.fetchApplicants.mockResolvedValue({
        items: mockApplicants,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      const user = userEvent.setup();
      render(<Home />);

      await waitFor(() => {
        expect(screen.getByTestId("mock-table")).toBeInTheDocument();
      });

      // Initial sort: created_at desc
      expect(mockApi.fetchApplicants).toHaveBeenCalledWith(
        expect.objectContaining({
          sortBy: "created_at",
          sortOrder: "desc",
        })
      );

      // Click sort by name (in mocked table)
      const sortButton = screen.getByRole("button", { name: "Sort by Name" });
      await user.click(sortButton);

      await waitFor(() => {
        expect(mockApi.fetchApplicants).toHaveBeenCalledWith(
          expect.objectContaining({
            sortBy: "name",
            sortOrder: "desc",
          })
        );
      });

      // Click again to reverse order
      await user.click(sortButton);

      await waitFor(() => {
        expect(mockApi.fetchApplicants).toHaveBeenCalledWith(
          expect.objectContaining({
            sortBy: "name",
            sortOrder: "asc",
          })
        );
      });
    });
  });

  describe("pagination", () => {
    it("displays pagination controls when multiple pages", async () => {
      mockApi.fetchApplicants.mockResolvedValue({
        items: mockApplicants,
        total: 50,
        page: 1,
        page_size: 20,
        total_pages: 3,
      });
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      render(<Home />);

      await waitFor(() => {
        expect(screen.getByText("Page 1 of 3")).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Previous" })).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Next" })).toBeInTheDocument();
      });
    });

    it("hides pagination when only one page", async () => {
      mockApi.fetchApplicants.mockResolvedValue({
        items: mockApplicants,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      render(<Home />);

      await waitFor(() => {
        expect(screen.getByText("2 applicants found")).toBeInTheDocument();
      });

      expect(screen.queryByText(/Page/)).not.toBeInTheDocument();
    });

    it("navigates to next page", async () => {
      mockApi.fetchApplicants.mockResolvedValue({
        items: mockApplicants,
        total: 50,
        page: 1,
        page_size: 20,
        total_pages: 3,
      });
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      const user = userEvent.setup();
      render(<Home />);

      await waitFor(() => {
        expect(screen.getByText("Page 1 of 3")).toBeInTheDocument();
      });

      const nextButton = screen.getByRole("button", { name: "Next" });
      await user.click(nextButton);

      await waitFor(() => {
        expect(mockApi.fetchApplicants).toHaveBeenCalledWith(
          expect.objectContaining({
            page: 2,
          })
        );
      });
    });

    it("navigates to previous page", async () => {
      mockApi.fetchApplicants.mockResolvedValue({
        items: mockApplicants,
        total: 50,
        page: 2,
        page_size: 20,
        total_pages: 3,
      });
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      const user = userEvent.setup();
      render(<Home />);

      await waitFor(() => {
        expect(screen.getByText("50 applicants found")).toBeInTheDocument();
      });

      // Go to next page first
      const nextButton = screen.getByRole("button", { name: "Next" });
      await user.click(nextButton);

      await waitFor(() => {
        expect(mockApi.fetchApplicants).toHaveBeenCalledWith(
          expect.objectContaining({ page: 2 })
        );
      });

      // Then go back
      const prevButton = screen.getByRole("button", { name: "Previous" });
      await user.click(prevButton);

      await waitFor(() => {
        expect(mockApi.fetchApplicants).toHaveBeenCalledWith(
          expect.objectContaining({ page: 1 })
        );
      });
    });

    it("disables Previous button on first page", async () => {
      mockApi.fetchApplicants.mockResolvedValue({
        items: mockApplicants,
        total: 50,
        page: 1,
        page_size: 20,
        total_pages: 3,
      });
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      render(<Home />);

      await waitFor(() => {
        expect(screen.getByText("Page 1 of 3")).toBeInTheDocument();
      });

      const prevButton = screen.getByRole("button", { name: "Previous" });
      expect(prevButton).toBeDisabled();
    });

    it("disables Next button on last page", async () => {
      mockApi.fetchApplicants.mockResolvedValue({
        items: mockApplicants,
        total: 50,
        page: 1,
        page_size: 20,
        total_pages: 3,
      });
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      const user = userEvent.setup();
      render(<Home />);

      await waitFor(() => {
        expect(screen.getByText("Page 1 of 3")).toBeInTheDocument();
      });

      // Navigate to last page (page 3)
      const nextButton = screen.getByRole("button", { name: "Next" });
      await user.click(nextButton);
      await user.click(nextButton);

      await waitFor(() => {
        expect(nextButton).toBeDisabled();
      });
    });
  });

  describe("sync and revalidate integration", () => {
    it("reloads applicants after sync completion", async () => {
      mockApi.fetchApplicants.mockResolvedValue({
        items: mockApplicants,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      const user = userEvent.setup();
      render(<Home />);

      await waitFor(() => {
        expect(mockApi.fetchApplicants).toHaveBeenCalledTimes(1);
      });

      // Trigger sync complete
      const syncCompleteButton = screen.getByRole("button", { name: "Complete Sync" });
      await user.click(syncCompleteButton);

      await waitFor(() => {
        expect(mockApi.fetchApplicants).toHaveBeenCalledTimes(2);
      });
    });

    it("reloads applicants after revalidation completion", async () => {
      mockApi.fetchApplicants.mockResolvedValue({
        items: mockApplicants,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      const user = userEvent.setup();
      render(<Home />);

      await waitFor(() => {
        expect(mockApi.fetchApplicants).toHaveBeenCalledTimes(1);
      });

      // Trigger revalidate complete
      const revalidateButton = screen.getByRole("button", { name: "Complete Revalidate" });
      await user.click(revalidateButton);

      await waitFor(() => {
        expect(mockApi.fetchApplicants).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe("empty state", () => {
    it("displays table even with no applicants", async () => {
      mockApi.fetchApplicants.mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      });
      mockApi.getTAs.mockResolvedValue([]);
      mockApi.getSources.mockResolvedValue([]);
      mockApi.getRiskLevels.mockResolvedValue([]);
      mockApi.getFlagTypes.mockResolvedValue([]);

      render(<Home />);

      await waitFor(() => {
        expect(screen.getByText("0 applicants found")).toBeInTheDocument();
      });

      expect(screen.getByTestId("mock-table")).toBeInTheDocument();
      expect(screen.getByTestId("applicant-count")).toHaveTextContent("0");
    });
  });
});
