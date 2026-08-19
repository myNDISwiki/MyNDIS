const config = {
  title: 'MyNDIS',
  tagline: 'Practical, independent information for navigating the NDIS',
  favicon: 'img/favicon.ico',

  url: 'https://myndiswiki.github.io',
  baseUrl: '/MyNDIS/',
  organizationName: 'myNDISwiki',
  projectName: 'MyNDIS',
  trailingSlash: true,

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  presets: [
    [
      'classic',
      {
        docs: {
          path: 'docs',
          routeBasePath: '/',
          sidebarPath: require.resolve('./sidebars.js'),
          showLastUpdateTime: true,
        },
        blog: false,
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
        sitemap: {
          changefreq: 'weekly',
          priority: 0.5,
        },
      },
    ],
  ],

  themeConfig: {
    navbar: {
      title: 'MyNDIS',
      items: [
        {to: '/apply/', label: 'I want to apply', position: 'left'},
        {to: '/on-the-ndis/', label: 'I am on the NDIS', position: 'left'},
        {to: '/questions/', label: 'Questions', position: 'left'},
        {to: '/keywords/', label: 'Keywords', position: 'left'},
      ],
    },
    footer: {
      style: 'light',
      links: [
        {
          title: 'MyNDIS',
          items: [
            {label: 'Apply for the NDIS', to: '/apply/'},
            {label: 'On the NDIS', to: '/on-the-ndis/'},
            {label: 'Questions', to: '/questions/'},
            {label: 'Keywords', to: '/keywords/'},
          ],
        },
        {
          title: 'Sources',
          items: [
            {label: 'NDIS website archive', href: '../archive/ndis/'},
            {label: 'Project repository', href: 'https://github.com/myNDISwiki/MyNDIS'},
          ],
        },
      ],
      copyright: 'MyNDIS is an independent information project and is not an official Australian Government or NDIA website. Information is maintained and updated as carefully as possible, but may become outdated or contain errors. Always check relevant official sources when making decisions about your NDIS supports, rights, or obligations.',
    },
  },
};

module.exports = config;
