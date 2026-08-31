// Copyright (c) 2015-present Mattermost, Inc. All Rights Reserved.
// See LICENSE.txt for license information.

import React from 'react';
import styled from 'styled-components';

import ProductBrandingFreeEdition from './product_branding_team_edition';

export const ProductMenuContainer = styled.nav`
    display: flex;
    align-items: center;
    min-width: 0;
    padding: 3px 6px 3px 5px;
`;

// Preserve the named export used by upstream tests/imports while deliberately
// rendering a non-interactive brand surface. No product switcher is mounted.
export const ProductMenuButton = styled.span`
    display: flex;
    align-items: center;
    min-width: 0;
`;

const ProductMenu = (): JSX.Element => (
    <ProductMenuContainer aria-label='NoBS'>
        <ProductMenuButton>
            <ProductBrandingFreeEdition/>
        </ProductMenuButton>
    </ProductMenuContainer>
);

export default ProductMenu;
