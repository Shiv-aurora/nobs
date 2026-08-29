// Copyright (c) 2015-present Mattermost, Inc. All Rights Reserved.
// See LICENSE.txt for license information.

import classNames from 'classnames';
import React from 'react';
import {Link} from 'react-router-dom';

import BackButton from 'components/common/back_button';

import brandMark from 'images/noping/logo.png';

import './header.scss';

export type HeaderProps = {
    alternateLink?: React.ReactElement;
    backButtonURL?: string;
    onBackButtonClick?: React.EventHandler<React.MouseEvent>;
};

const Header = ({alternateLink, backButtonURL, onBackButtonClick}: HeaderProps) => (
    <div
        data-testid='hfroute-header'
        className={classNames('hfroute-header', 'has-custom-site-name')}
    >
        <div className='header-main'>
            <div>
                <Link
                    data-testid='header-logo-link'
                    className='header-logo-link noping-header-logo-link'
                    to='/'
                    aria-label='NoBS'
                >
                    <img
                        className='noping-header-mark'
                        src={brandMark}
                        alt=''
                    />
                    <span className='noping-header-name'>NoBS</span>
                </Link>
            </div>
            {alternateLink}
        </div>
        {onBackButtonClick && (
            <BackButton
                className='header-back-button'
                url={backButtonURL}
                onClick={onBackButtonClick}
            />
        )}
    </div>
);

export default Header;
