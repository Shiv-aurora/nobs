import type React from 'react';

type RouteComponent = React.ComponentType<Record<string, never>>;
type HeaderComponent = React.ComponentType<Record<string, never>>;

export interface PluginRegistry {
    /** Preferred product-level registration on current Mattermost releases. */
    registerProduct?: (
        route: string,
        switcherIcon: React.ReactNode,
        switcherText: React.ReactNode,
        switcherLinkURL: string,
        component: RouteComponent,
        headerCenterComponent: HeaderComponent,
        headerRightComponent: HeaderComponent,
        showTeamSidebar: boolean,
        showAppBar?: boolean,
        wrapped?: boolean,
        publicComponent?: React.ComponentType,
        isTeamScoped?: boolean,
    ) => void;
    /** Team-scoped fallback for releases without product registration. */
    registerNeedsTeamRoute?: (path: string, component: RouteComponent) => void;
    /** Root-scoped compatibility fallback. */
    registerCustomRoute(path: string, component: RouteComponent): void;
    registerMainMenuAction(text: string, action: () => void): void;
    registerChannelHeaderButtonAction(
        icon: React.ReactNode,
        action: () => void,
        dropdownText: string,
        tooltipText: string,
    ): void;
    registerWebSocketEventHandler(event: string, handler: (message: unknown) => void): void;
}
