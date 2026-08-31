// Copyright (c) 2015-present Mattermost, Inc. All Rights Reserved.
// See LICENSE.txt for license information.

import React from 'react';
import styled from 'styled-components';

import brandMark from 'images/noping/logo.png';

const NoBSBrand = styled.span`
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: rgba(255, 255, 255, .94);
    font-size: 18px;
    font-weight: 800;
    letter-spacing: -.04em;
`;

const NoBSMark = styled.img`
    width: 27px;
    height: 27px;
    object-fit: contain;
`;

const ProductBrandingFreeEdition = (): JSX.Element => (
    <NoBSBrand aria-label='NoBS'>
        <NoBSMark src={brandMark} alt=''/>
        NoBS
    </NoBSBrand>
);

export default ProductBrandingFreeEdition;
