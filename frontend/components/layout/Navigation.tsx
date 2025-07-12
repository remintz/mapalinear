import React from 'react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

interface NavigationProps {
  className?: string;
}

export function Navigation({ className }: NavigationProps) {
  return (
    <nav className={cn('bg-white border-b border-gray-200', className)}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link 
              href="/" 
              className="text-xl font-bold text-blue-600 hover:text-blue-700"
            >
              MapaLinear
            </Link>
          </div>
          
          <div className="flex items-center space-x-6">
            <Link 
              href="/search" 
              className="text-gray-600 hover:text-gray-900 transition-colors"
            >
              Buscar Rota
            </Link>
            <Link 
              href="/history" 
              className="text-gray-600 hover:text-gray-900 transition-colors"
            >
              Histórico
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}