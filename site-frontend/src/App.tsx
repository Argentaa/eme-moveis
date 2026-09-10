/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import Hero from './pages/Hero';
import About from './pages/About';
import Timeline from './pages/Timeline';
import Portfolio from './pages/Portfolio';
import Contact from './pages/Contact';
import Admin from './pages/Admin';

/**
 * Main App component.
 * Assembles all sections into a single-page modern landing page for EME Móveis.
 */
export default function App() {
  const [isAdminRoute, setIsAdminRoute] = useState(false);

  useEffect(() => {
    const handlePathCheck = () => {
      setIsAdminRoute(window.location.pathname === '/admin' || window.location.pathname.startsWith('/admin/'));
    };

    handlePathCheck();
    window.addEventListener('popstate', handlePathCheck);
    return () => window.removeEventListener('popstate', handlePathCheck);
  }, []);

  if (isAdminRoute) {
    return <Admin />;
  }

  return (
    <div className="flex flex-col min-h-screen">
      {/* Fixed Sticky Navigation */}
      <Navbar />

      <main className="flex-grow">
        {/* Each section has an ID that matches Navbar links */}
        <Hero />
        <About />
        <Timeline />
        <Portfolio />
        <Contact />
      </main>

      {/* Persistent Footer */}
      <Footer />
    </div>
  );
}

