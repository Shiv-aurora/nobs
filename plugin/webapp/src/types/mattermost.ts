import type React from 'react';

export interface PluginRegistry {
    registerCustomRoute(path: string, component: React.ComponentType): void;
    registerMainMenuAction(text: string, action: () => void): void;
    registerChannelHeaderButtonAction(icon: React.ReactNode, action: () => void, tooltipText: string): void;
    registerWebSocketEventHandler(event: string, handler: (message: unknown) => void): void;
}
