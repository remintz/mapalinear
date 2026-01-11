"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useSession } from 'next-auth/react';
import { cn } from '@/lib/utils';
import { LoginButton } from '@/components/auth/LoginButton';
import { Shield, Menu, X } from 'lucide-react';

interface NavigationProps {
  className?: string;
}

export function Navigation({ className }: NavigationProps) {
  const { data: session } = useSession();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  // Close menu when pressing Escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsMenuOpen(false);
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, []);

  // Prevent body scroll when menu is open
  useEffect(() => {
    if (isMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isMenuOpen]);

  const closeMenu = () => setIsMenuOpen(false);

  const NavLinks = ({ mobile = false }: { mobile?: boolean }) => (
    <>
      <Link
        href="/search"
        onClick={mobile ? closeMenu : undefined}
        className={cn(
          "text-gray-600 hover:text-gray-900 transition-colors",
          mobile && "block py-3 text-lg border-b border-gray-100"
        )}
      >
        Criar Mapa
      </Link>
      <Link
        href="/maps"
        onClick={mobile ? closeMenu : undefined}
        className={cn(
          "text-gray-600 hover:text-gray-900 transition-colors",
          mobile && "block py-3 text-lg border-b border-gray-100"
        )}
      >
        Meus Mapas
      </Link>
      {session?.user?.isAdmin && (
        <Link
          href="/admin"
          onClick={mobile ? closeMenu : undefined}
          className={cn(
            "flex items-center gap-1.5 text-blue-600 hover:text-blue-700 transition-colors",
            mobile && "py-3 text-lg border-b border-gray-100"
          )}
        >
          <Shield className="w-4 h-4" />
          Admin
        </Link>
      )}
    </>
  );

  return (
    <nav className={cn('bg-white border-b border-gray-200', className)}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-14 sm:h-16">
          {/* Logo */}
          <Link
            href="/"
            className="text-xl font-bold text-blue-600 hover:text-blue-700 flex-shrink-0"
          >
            OraPOIS
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-6">
            <NavLinks />
            <div className="border-l border-gray-200 h-6 mx-2"></div>
            <LoginButton />
          </div>

          {/* Mobile: Login + Menu Button */}
          <div className="flex md:hidden items-center gap-2">
            <LoginButton />
            <button
              onClick={() => setIsMenuOpen(true)}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              aria-label="Abrir menu"
            >
              <Menu className="w-6 h-6" />
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Overlay */}
      <div
        className={cn(
          "fixed inset-0 bg-black/50 z-40 md:hidden transition-opacity duration-300",
          isMenuOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        onClick={closeMenu}
      />

      {/* Mobile Menu Drawer */}
      <div
        className={cn(
          "fixed top-0 right-0 h-full w-72 bg-white z-50 md:hidden transform transition-transform duration-300 ease-in-out shadow-xl",
          isMenuOpen ? "translate-x-0" : "translate-x-full"
        )}
      >
        <div className="flex flex-col h-full">
          {/* Drawer Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <span className="text-lg font-semibold text-gray-900">Menu</span>
            <button
              onClick={closeMenu}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              aria-label="Fechar menu"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Drawer Content */}
          <div className="flex-1 overflow-y-auto p-4">
            <NavLinks mobile />
          </div>
        </div>
      </div>
    </nav>
  );
}
