export interface MattermostUser {
    id: string;
    username: string;
    first_name: string;
    last_name: string;
    nickname: string;
    roles: string;
}

export interface MattermostTeam {
    id: string;
    name: string;
    display_name: string;
}

export interface MattermostChannel {
    id: string;
    team_id: string;
    type: 'O' | 'P' | 'D' | 'G';
    display_name: string;
    name: string;
    purpose: string;
    header: string;
    total_msg_count: number;
    last_post_at: number;
}

export interface MattermostPost {
    id: string;
    create_at: number;
    update_at: number;
    user_id: string;
    channel_id: string;
    root_id: string;
    message: string;
    type: string;
    props: Record<string, unknown>;
    reply_count: number;
}

export interface MattermostPostsResponse {
    order: string[];
    posts: Record<string, MattermostPost>;
}

export interface MessagingBootstrap {
    currentUser: MattermostUser;
    team: MattermostTeam;
    channels: MattermostChannel[];
}
