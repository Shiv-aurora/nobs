import type React from 'react';

type RouteComponent = React.ComponentType<Record<string, never>>;
type HeaderComponent = React.ComponentType<Record<string, never>>;

export interface PluginStore {
    dispatch(action: unknown): unknown;
}

interface AppBarRegistration {
    id: string;
    rhsComponent: {
        showRHSPlugin: unknown;
        hideRHSPlugin: unknown;
        toggleRHSPlugin: unknown;
    };
}

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
    registerAppBarComponent?: (
        iconURL: string,
        action: undefined,
        tooltipText: React.ReactNode,
        supportedProductIDs: string,
        rhsComponent: React.ComponentType,
        rhsTitle: React.ReactNode,
    ) => AppBarRegistration | string;
    registerPostHeaderComponent?: (component: React.ComponentType<{post: {props?: Record<string, unknown>}}>) => string;
    registerPostDropdownMenuAction?: (text: React.ReactNode, action: (postID: string) => void, filter: (postID: string) => boolean) => string;
    registerChannelHeaderButtonAction(
        icon: React.ReactNode,
        action: () => void,
        dropdownText: string,
        tooltipText: string,
    ): void;
    registerWebSocketEventHandler(event: string, handler: (message: unknown) => void): void;
    registerPopoverUserActionsComponent?: (component: React.ComponentType) => string;
}
