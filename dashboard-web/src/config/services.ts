export interface Service {
  name: string;
  url: string;
  icon: string;
  color: string;
}

export const services: Service[] = [
  { 
    name: "Catflix", 
    url: "http://192.168.0.102:8096", 
    icon: "play-circle", 
    color: "#ff7043" 
  },
  { 
    name: "Fotky", 
    url: "http://192.168.0.102:2283", 
    icon: "camera", 
    color: "#cc34eb" 
  },
  { 
    name: "Home Assistant", 
    url: "http://192.168.0.102:8123", 
    icon: "home", 
    color: "#fbc02d" 
  },
  { 
    name: "Pi-hole", 
    url: "http://pihole.local/admin/login", 
    icon: "shield", 
    color: "#4caf50" 
  },
  { 
    name: "NAS", 
    url: "http://192.168.0.102", 
    icon: "database", 
    color: "#2196f3" 
  },
];
