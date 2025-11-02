import { useState, useEffect, useMemo } from "react";
import { Server } from "lucide-react";
import ServiceTile from "@/components/ServiceTile";
import SearchBar from "@/components/SearchBar";
import ViewToggle, { ViewMode } from "@/components/ViewToggle";
import { services } from "@/config/services";
import { cn } from "@/lib/utils";

const Index = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");

  // Load view mode from localStorage
  useEffect(() => {
    const savedViewMode = localStorage.getItem("viewMode") as ViewMode;
    if (savedViewMode) {
      setViewMode(savedViewMode);
    }
  }, []);

  // Save view mode to localStorage
  const handleViewModeChange = (mode: ViewMode) => {
    setViewMode(mode);
    localStorage.setItem("viewMode", mode);
  };

  // Filter services based on search query
  const filteredServices = useMemo(() => {
    if (!searchQuery.trim()) return services;
    
    const query = searchQuery.toLowerCase();
    return services.filter(service => 
      service.name.toLowerCase().includes(query) ||
      service.url.toLowerCase().includes(query)
    );
  }, [searchQuery]);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/50 bg-card/30 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-6">
          <div className="flex flex-col md:flex-row items-center gap-6 md:gap-8">
            {/* Logo & Title */}
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center">
                <Server className="w-6 h-6 text-primary" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-foreground">
                  Homelab Dashboard
                </h1>
                <p className="text-sm text-muted-foreground">
                  Správa domácích služeb
                </p>
              </div>
            </div>

            {/* Search & View Toggle */}
            <div className="flex-1 flex items-center gap-4 w-full md:w-auto justify-center md:justify-end">
              <SearchBar value={searchQuery} onChange={setSearchQuery} />
              <ViewToggle viewMode={viewMode} onToggle={handleViewModeChange} />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {/* Services Grid */}
        {filteredServices.length > 0 ? (
          <div 
            className={cn(
              "gap-6",
              viewMode === "grid" 
                ? "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" 
                : "flex flex-col max-w-3xl mx-auto"
            )}
          >
            {filteredServices.map((service) => (
              <ServiceTile
                key={service.name}
                name={service.name}
                url={service.url}
                icon={service.icon}
                color={service.color}
                isCompact={viewMode === "compact"}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-16">
            <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-muted/50 flex items-center justify-center">
              <Server className="w-10 h-10 text-muted-foreground" />
            </div>
            <h2 className="text-xl font-semibold text-foreground mb-2">
              Žádné služby nenalezeny
            </h2>
            <p className="text-muted-foreground">
              Zkuste upravit vyhledávací dotaz
            </p>
          </div>
        )}

        {/* Footer Info */}
        <div className="mt-12 pt-8 border-t border-border/50">
          <div className="text-center text-sm text-muted-foreground">
            <p className="mb-2">
              Celkem služeb: <span className="font-semibold text-foreground">{services.length}</span>
            </p>
            <p className="text-xs">
              Dimitrij Fedoryno
              <code className="px-2 py-1 bg-card rounded text-primary">src/config/services.ts</code>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Index;
