# Frontend Test Coverage Summary

## Overview
This document summarizes the test files created to improve frontend test coverage. All tests follow the patterns established in the existing test file (`src/__tests__/app/applicants/detail.test.tsx`) and use Jest + React Testing Library.

## Test Files Created

### 1. API Client Tests (`src/__tests__/lib/api.test.ts`)
**Purpose**: Test all API client functions that communicate with the backend

**Coverage Areas**:
- **Applicant endpoints**: `fetchApplicants`, `fetchApplicant`, `updateApplicantReviewed`
- **Sync API**: `getSyncStatus`, `startSync`, `getApplicantCount`
- **Filter options**: `getTAs`, `getSources`, `getFlagTypes`, `getRiskLevels`
- **Validation rules**: `getValidationRules`
- **Disposable domains**: `getDisposableDomains`, `addDisposableDomain`, `removeDisposableDomain`, `syncDisposableDomains`
- **Integration settings**: `getIntegrations`, `updateIntegration`, `testIntegration`
- **Re-validation**: `getRevalidateStatus`, `startRevalidation`
- **Admin endpoints**: `getDatabaseStats`, `purgeDatabase`
- **Single applicant validation**: `validateApplicant`

**Key Test Patterns**:
- Uses mocked `fetch` to avoid real HTTP calls
- Tests both success and error scenarios
- Verifies correct URL construction with query parameters
- Tests error handling for specific HTTP status codes (404, 409, 400, etc.)

**Example Test**:
```typescript
it("fetches applicants with default parameters", async () => {
  const mockResponse = {
    items: [/* mock data */],
    total: 1,
    total_pages: 1,
    page: 1,
    page_size: 20,
  };

  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => mockResponse,
  } as Response);

  const result = await api.fetchApplicants();
  expect(result).toEqual(mockResponse);
});
```

---

### 2. Auth Context Tests (`src/__tests__/lib/auth-context.test.tsx`)
**Purpose**: Test the authentication context provider and hook

**Coverage Areas**:
- **Hook validation**: Ensures `useAuth` throws error when used outside provider
- **Initialization**: User fetch on mount, handling 401 responses
- **Login**: Successful login, redirect to home vs setup page, error handling
- **Logout**: Successful logout, redirect to login, error recovery
- **Role checks**: `isAdmin`, `isSuperAdmin`, regular user roles
- **Route protection**: Redirects based on auth state and required setup

**Key Test Patterns**:
- Custom test component that uses the hook
- Mocked `useRouter` and `usePathname` from Next.js
- Tests for redirect behavior
- Role-based access control verification

**Example Test**:
```typescript
it("successfully logs in and redirects to home", async () => {
  const mockUser = { /* ... */ };
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => mockUser,
  } as Response);

  await user.click(loginButton);

  await waitFor(() => {
    expect(screen.getByTestId("user")).toHaveTextContent("test@example.com");
  });
  expect(mockPush).toHaveBeenCalledWith("/");
});
```

---

### 3. Login Page Tests (`src/__tests__/app/login/page.test.tsx`)
**Purpose**: Test the login page UI and behavior

**Coverage Areas**:
- **Rendering**: Form fields, labels, placeholders, attributes
- **Form validation**: Disabled state when fields empty, enabled when filled
- **Submission**: Calls login function, loading states, disabled inputs
- **Error handling**: Display error messages, clear on new submission
- **Accessibility**: Label associations, proper ARIA attributes
- **Keyboard navigation**: Enter key submission, tab between fields
- **Input behavior**: Value updates, password masking

**Key Test Patterns**:
- Mocked `useAuth` hook
- User event testing with `@testing-library/user-event`
- Loading state verification
- Error message display and clearing

**Example Test**:
```typescript
it("calls login with email and password on submit", async () => {
  mockLogin.mockResolvedValueOnce(undefined);
  const user = userEvent.setup();

  await user.type(emailInput, "test@example.com");
  await user.type(passwordInput, "password123");
  await user.click(submitButton);

  expect(mockLogin).toHaveBeenCalledWith("test@example.com", "password123");
});
```

---

### 4. Main Page Tests (`src/__tests__/app/page.test.tsx`)
**Purpose**: Test the main applicants listing page

**Coverage Areas**:
- **Initial rendering**: Header, description, panels, table
- **Loading state**: Loading message, disabled interactions
- **Data fetching**: Applicants, filter options (TAs, sources, risk levels, flags)
- **Error handling**: Error display, retry button functionality
- **Filtering**: TA, source, risk level, flag type filters; page reset on filter change
- **Sorting**: Toggle sort order, change sort field
- **Pagination**: Controls display, navigation, disabled states
- **Sync/revalidate integration**: Reload applicants after operations
- **Empty state**: Display with no applicants

**Key Test Patterns**:
- Mocked child components (Header, ApplicantsTable, SyncPanel, etc.)
- Comprehensive filter testing
- Pagination edge cases (first/last page)
- Integration with sync operations

**Example Test**:
```typescript
it("navigates to next page", async () => {
  mockApi.fetchApplicants.mockResolvedValue({
    items: mockApplicants,
    total: 50,
    page: 1,
    page_size: 20,
    total_pages: 3,
  });

  const nextButton = screen.getByRole("button", { name: "Next" });
  await user.click(nextButton);

  await waitFor(() => {
    expect(mockApi.fetchApplicants).toHaveBeenCalledWith(
      expect.objectContaining({ page: 2 })
    );
  });
});
```

---

### 5. Header Component Tests (`src/__tests__/components/header.test.tsx`)
**Purpose**: Test the navigation header component

**Coverage Areas**:
- **Branding**: Logo, app title, home link
- **Navigation links**: Regular user vs admin views, active link highlighting
- **Validation Data dropdown**: Open/close, menu items
- **User menu (logged out)**: Sign In button
- **User menu (logged in)**: Avatar, name, email, role badge, Sign Out
- **Admin features**: Manage Users link for admins only
- **Role badge colors**: Purple (superadmin), blue (admin), green (user)
- **Mobile menu**: Toggle, navigation items, admin sections
- **Accessibility**: ARIA attributes, proper roles

**Key Test Patterns**:
- Different user roles (user, admin, superadmin)
- Mocked `usePathname` for active state
- Dropdown interaction testing
- Mobile menu behavior

**Example Test**:
```typescript
it("calls logout when Sign Out is clicked", async () => {
  const user = userEvent.setup();

  const userButton = screen.getByText("Test User").closest("button");
  await user.click(userButton!);

  const signOutButton = screen.getByRole("button", { name: "Sign Out" });
  await user.click(signOutButton);

  expect(mockLogout).toHaveBeenCalled();
});
```

---

## Test Coverage Metrics

### Files Tested
- ✅ `src/lib/api.ts` - API client (100+ tests)
- ✅ `src/lib/auth-context.tsx` - Auth context (50+ tests)
- ✅ `src/app/login/page.tsx` - Login page (30+ tests)
- ✅ `src/app/page.tsx` - Main page (40+ tests)
- ✅ `src/components/header.tsx` - Header component (35+ tests)

### Total Tests Created
**~260+ test cases** across 5 test files

### Testing Approach
1. **Unit Tests**: Individual functions and components in isolation
2. **Integration Tests**: Component interactions with mocked dependencies
3. **Behavioral Tests**: User interactions and workflows
4. **Error Cases**: Network failures, invalid states, edge cases
5. **Accessibility**: ARIA attributes, keyboard navigation, semantic HTML

---

## Running the Tests

### Run all tests
```bash
cd frontend
npm run test
```

### Run tests with coverage
```bash
npm run test:coverage
```

### Run specific test file
```bash
npm run test -- api.test.ts
```

### Run tests in watch mode
```bash
npm run test:watch
```

---

## Test Patterns and Best Practices

### 1. Mocking External Dependencies
```typescript
// Mock API module
jest.mock("@/lib/api");
const mockApi = api as jest.Mocked<typeof api>;

// Mock Next.js navigation
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), /* ... */ }),
  usePathname: () => "/",
}));
```

### 2. User Event Testing
```typescript
const user = userEvent.setup();
await user.type(input, "text");
await user.click(button);
```

### 3. Waiting for Async Updates
```typescript
await waitFor(() => {
  expect(screen.getByText("Expected")).toBeInTheDocument();
});
```

### 4. Testing Loading States
```typescript
mockApi.fetchData.mockImplementation(
  () => new Promise(() => {}) // Never resolves
);
render(<Component />);
expect(screen.getByText("Loading...")).toBeInTheDocument();
```

### 5. Testing Error States
```typescript
mockApi.fetchData.mockRejectedValue(new Error("Network error"));
render(<Component />);
await waitFor(() => {
  expect(screen.getByText("Network error")).toBeInTheDocument();
});
```

---

## Still Needs Testing

### High Priority Components
1. `src/components/applicants-table.tsx` - Main data table
2. `src/components/sync-panel.tsx` - Sync operations panel
3. `src/app/admin/page.tsx` - Admin page
4. `src/app/settings/page.tsx` - Settings page
5. `src/app/users/page.tsx` - User management

### Medium Priority Pages
6. `src/app/rules/page.tsx` - Validation rules page
7. `src/app/validation-data/disposable-domains/page.tsx`
8. `src/app/validation-data/voip/page.tsx`
9. `src/app/setup/page.tsx` - Initial setup page
10. `src/app/change-password/page.tsx` - Change password page

### Lower Priority Components
11. `src/components/revalidate-panel.tsx`
12. `src/components/protected-route.tsx`
13. UI components in `src/components/ui/`

---

## Next Steps

1. **Run the tests** to verify they all pass
2. **Check coverage** with `npm run test:coverage`
3. **Create additional tests** for remaining components
4. **Integrate with CI/CD** to run tests on every commit
5. **Set coverage thresholds** in jest.config.ts

---

## Notes

- All tests follow the patterns from the existing `detail.test.tsx` file
- Mock implementations avoid making real HTTP requests
- Tests focus on user behavior rather than implementation details
- Accessibility testing is included where applicable
- Tests are organized by feature and behavior

---

## Common Issues and Solutions

### Issue: Tests timing out
**Solution**: Ensure all async operations are properly awaited and promises resolve/reject

### Issue: "Not wrapped in act()" warnings
**Solution**: Use `waitFor()` for async state updates and `userEvent` for interactions

### Issue: Navigation mocks not working
**Solution**: Ensure `useRouter` and `usePathname` are mocked before rendering components

### Issue: Component state not updating
**Solution**: Use `await waitFor()` to wait for state changes after async operations
