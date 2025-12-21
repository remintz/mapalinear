"use client";

import React from 'react';
import Link from 'next/link';
import { useSession } from 'next-auth/react';
import { cn } from '@/lib/utils';
import { LoginButton } from '@/components/auth/LoginButton';
import { Shield } from 'lucide-react';

interface NavigationProps {
  className?: string;
}

export function Navigation({ className }: NavigationProps) {
  const { data: session } = useSession();

  return (
    <nav className={cn('bg-white border-b border-gray-200', className)}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link
              href="/"
              className="text-xl font-bold text-blue-600 hover:text-blue-700"
            >
              OraPOIS
            </Link>
          </div>

          <div className="flex items-center space-x-4">
            <Link
              href="/search"
              className="text-gray-600 hover:text-gray-900 transition-colors"
            >
              Criar Mapa
            </Link>
            <Link
              href="/maps"
              className="text-gray-600 hover:text-gray-900 transition-colors"
            >
              Mapas Salvos
            </Link>
            {session?.user?.isAdmin && (
              <>
                <div className="border-l border-gray-200 h-6 mx-2"></div>
                <Link
                  href="/admin"
                  className="flex items-center gap-1.5 text-blue-600 hover:text-blue-700 transition-colors"
                >
                  <Shield className="w-4 h-4" />
                  Admin
                </Link>
              </>
            )}
            <div className="border-l border-gray-200 h-6 mx-2"></div>
            <LoginButton />
          </div>
        </div>
      </div>
    </nav>
  );
}
