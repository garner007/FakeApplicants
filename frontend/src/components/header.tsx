"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";

interface NavLinkProps {
  href: string;
  children: React.ReactNode;
  isActive: boolean;
}

function NavLink({ href, children, isActive }: NavLinkProps) {
  return (
    <Link
      href={href}
      className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
        isActive
          ? "bg-gray-900 text-white"
          : "text-gray-700 hover:bg-gray-100 hover:text-gray-900"
      }`}
    >
      {children}
    </Link>
  );
}

interface DropdownMenuProps {
  label: string;
  isActive: boolean;
  children: React.ReactNode;
}

function DropdownMenu({ label, isActive, children }: DropdownMenuProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div
      className="relative"
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
    >
      <button
        className={`px-3 py-2 rounded-md text-sm font-medium transition-colors inline-flex items-center gap-1 ${
          isActive
            ? "bg-gray-900 text-white"
            : "text-gray-700 hover:bg-gray-100 hover:text-gray-900"
        }`}
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        {label}
        <svg
          className={`w-4 h-4 transition-transform ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute left-0 mt-1 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-50">
          <div className="py-1">{children}</div>
        </div>
      )}
    </div>
  );
}

interface DropdownItemProps {
  href: string;
  children: React.ReactNode;
  isActive: boolean;
}

function DropdownItem({ href, children, isActive }: DropdownItemProps) {
  return (
    <Link
      href={href}
      className={`block px-4 py-2 text-sm transition-colors ${
        isActive
          ? "bg-gray-100 text-gray-900 font-medium"
          : "text-gray-700 hover:bg-gray-50 hover:text-gray-900"
      }`}
    >
      {children}
    </Link>
  );
}

export function Header() {
  const pathname = usePathname();

  const isApplicantsActive = pathname === "/" || pathname.startsWith("/applicants");
  const isRulesActive = pathname === "/rules";
  const isSettingsActive = pathname === "/settings";
  const isValidationDataActive = pathname.startsWith("/validation-data");
  const isDisposableDomainsActive = pathname === "/validation-data/disposable-domains";
  const isVoIPActive = pathname === "/validation-data/voip";

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo / App Title */}
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gray-900 rounded-md flex items-center justify-center">
              <svg
                className="w-5 h-5 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
            </div>
            <span className="text-xl font-bold text-gray-900">
              Applicant Validator
            </span>
          </Link>

          {/* Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            <NavLink href="/" isActive={isApplicantsActive}>
              Applicants
            </NavLink>
            <NavLink href="/rules" isActive={isRulesActive}>
              Validation Rules
            </NavLink>
            <NavLink href="/settings" isActive={isSettingsActive}>
              Integration Settings
            </NavLink>
            <DropdownMenu label="Validation Data" isActive={isValidationDataActive}>
              <DropdownItem
                href="/validation-data/disposable-domains"
                isActive={isDisposableDomainsActive}
              >
                Disposable Domains
              </DropdownItem>
              <DropdownItem href="/validation-data/voip" isActive={isVoIPActive}>
                VoIP Carriers
              </DropdownItem>
            </DropdownMenu>
          </nav>

          {/* Mobile menu button */}
          <MobileMenu
            isApplicantsActive={isApplicantsActive}
            isRulesActive={isRulesActive}
            isSettingsActive={isSettingsActive}
            isDisposableDomainsActive={isDisposableDomainsActive}
            isVoIPActive={isVoIPActive}
          />
        </div>
      </div>
    </header>
  );
}

interface MobileMenuProps {
  isApplicantsActive: boolean;
  isRulesActive: boolean;
  isSettingsActive: boolean;
  isDisposableDomainsActive: boolean;
  isVoIPActive: boolean;
}

function MobileMenu({
  isApplicantsActive,
  isRulesActive,
  isSettingsActive,
  isDisposableDomainsActive,
  isVoIPActive,
}: MobileMenuProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="md:hidden">
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Toggle menu"
      >
        {isOpen ? (
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        ) : (
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 6h16M4 12h16M4 18h16"
            />
          </svg>
        )}
      </Button>

      {isOpen && (
        <div className="absolute top-16 left-0 right-0 bg-white border-b border-gray-200 shadow-lg z-50">
          <nav className="container mx-auto px-4 py-4 flex flex-col gap-2">
            <Link
              href="/"
              className={`px-3 py-2 rounded-md text-sm font-medium ${
                isApplicantsActive
                  ? "bg-gray-900 text-white"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
              onClick={() => setIsOpen(false)}
            >
              Applicants
            </Link>
            <Link
              href="/rules"
              className={`px-3 py-2 rounded-md text-sm font-medium ${
                isRulesActive
                  ? "bg-gray-900 text-white"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
              onClick={() => setIsOpen(false)}
            >
              Validation Rules
            </Link>
            <Link
              href="/settings"
              className={`px-3 py-2 rounded-md text-sm font-medium ${
                isSettingsActive
                  ? "bg-gray-900 text-white"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
              onClick={() => setIsOpen(false)}
            >
              Integration Settings
            </Link>
            <div className="border-t border-gray-200 pt-2 mt-2">
              <p className="px-3 py-1 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Validation Data
              </p>
              <Link
                href="/validation-data/disposable-domains"
                className={`px-3 py-2 rounded-md text-sm font-medium block ${
                  isDisposableDomainsActive
                    ? "bg-gray-900 text-white"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
                onClick={() => setIsOpen(false)}
              >
                Disposable Domains
              </Link>
              <Link
                href="/validation-data/voip"
                className={`px-3 py-2 rounded-md text-sm font-medium block ${
                  isVoIPActive
                    ? "bg-gray-900 text-white"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
                onClick={() => setIsOpen(false)}
              >
                VoIP Carriers
              </Link>
            </div>
          </nav>
        </div>
      )}
    </div>
  );
}
