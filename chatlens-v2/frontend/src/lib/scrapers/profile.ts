import * as cheerio from 'cheerio';
import type { Element, AnyNode } from 'domhandler';
import {
  ERP_URL,
  ERP_ENDPOINTS,
  ScraperSession,
  arrayToJar,
  fetchWithJar,
  checkRateLimitText,
} from './http-jar';

export async function fetchProfileData(session: ScraperSession) {
  const jar = arrayToJar(session.cookies);
  const res = await fetchWithJar(ERP_ENDPOINTS['profile'], jar, {
    method: 'GET',
    extraHeaders: { Origin: ERP_URL, Referer: ERP_URL },
  });
  const html = await res.text();
  checkRateLimitText(html);
  if (html.includes('id="login-form"'))
    throw new Error('Session expired or invalid ERP route.');

  const tabUrls = new Map<string, string>();
  const $ = cheerio.load(html);

  $('a').each((_i: number, a: Element) => {
    const href = $(a).attr('href');
    const text = $(a).text().trim();
    if (
      href &&
      href.includes('index.php?r=') &&
      !href.includes('viewprofileindi')
    ) {
      if (
        $(a).parents('li, .nav, .tabs, .ui-tabs-nav, .tab-pane, .panel')
          .length > 0
      ) {
        tabUrls.set(href, text || 'Unknown Tab');
      }
    }
  });

  const scriptRegex1 =
    /'([^']+)'\s*:\s*\{\s*'ajax'\s*:\s*'(\/index\.php\?r=[^']+)'/gi;
  let match1;
  while ((match1 = scriptRegex1.exec(html)) !== null) {
    if (!match1[2].includes('viewprofileindi')) {
      tabUrls.set(match1[2].replace('&amp;', '&'), match1[1]);
    }
  }

  const scriptRegex2 = /'url'\s*:\s*'(\/index\.php\?r=[^']+)'/gi;
  let match2;
  while ((match2 = scriptRegex2.exec(html)) !== null) {
    if (!match2[1].includes('viewprofileindi')) {
      const u = match2[1].replace('&amp;', '&');
      if (!tabUrls.has(u)) {
        tabUrls.set(u, 'Unknown Tab');
      }
    }
  }

  const entries = Array.from(tabUrls.entries());
  const BATCH_SIZE = 3;
  const tabHtmls: { name: string; html: string }[] = [];

  for (let i = 0; i < entries.length; i += BATCH_SIZE) {
    if (i > 0) {
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
    const batch = entries.slice(i, i + BATCH_SIZE);
    const batchResults = await Promise.all(
      batch.map(async ([url, name]) => {
        try {
          const tabRes = await fetchWithJar(
            `https://newerp.kluniversity.in${url}`,
            jar,
            {
              method: 'GET',
              extraHeaders: {
                Origin: ERP_URL,
                Referer: ERP_ENDPOINTS['profile'],
                'X-Requested-With': 'XMLHttpRequest',
              },
              signal: AbortSignal.timeout(3500),
            }
          );
          return { name, html: await tabRes.text() };
        } catch {
          return { name, html: '' };
        }
      })
    );
    tabHtmls.push(...batchResults);
  }

  const allPages = [{ name: 'Personal Information', html }, ...tabHtmls];

  return { success: true, data: parseProfileData(allPages) };
}

function parseProfileData(pages: { name: string; html: string }[]) {
  const mainHtml = pages[0].html;
  const $main = cheerio.load(mainHtml);
  const text = $main.text();

  const data: Record<string, unknown> = {
    name: '',
    universityId: '',
    photoUrl: '',
    success: true,
  };

  const profileBg = $main('.profile_bg');
  const nameEl = profileBg
    .find('h4')
    .filter(
      (_i: number, el: Element) => !$main(el).text().includes('Student Profile')
    );
  let name =
    nameEl.text().trim() ||
    profileBg
      .contents()
      .filter(
        (_i: number, el: AnyNode) =>
          (el as unknown as { type?: string }).type === 'text'
      )
      .text()
      .trim();

  if (!name || name.length < 3) {
    const welcomeMatch = text.match(
      /(?:Welcome|Hello|Name)[\s:-]*([A-Za-z\s]{4,40})(?:\s|\||$)/i
    );
    if (welcomeMatch) name = welcomeMatch[1].trim();
  }
  if (name) data.name = name.replace(/University ID.*/i, '').trim();

  const uidMatch = text.match(/University\s*ID\s*[:\s]*(\d+)/i);
  if (uidMatch) data.universityId = uidMatch[1];

  $main('img').each((_i: number, img: Element) => {
    const src = $main(img).attr('src');
    if (src) {
      const lowerSrc = src.toLowerCase();
      if (
        lowerSrc.endsWith('.js') ||
        lowerSrc.includes('logo') ||
        lowerSrc.includes('captcha')
      )
        return;

      const uid = (data.universityId as string) || '';
      if (
        lowerSrc.includes('studentphotos') ||
        lowerSrc.includes('profile') ||
        (uid && src.includes(uid))
      ) {
        data.photoUrl = src;
      }
    }
  });
  if (!data.photoUrl) {
    const imgMatch = mainHtml.match(
      /<img[^>]*src=["']([^"']*(?:studentphotos|profile|uploads|data:\s*image)[^"']*)["']/i
    );
    if (imgMatch && !imgMatch[1].toLowerCase().endsWith('.js')) {
      let photoSrc = imgMatch[1];
      if (photoSrc.replace(/\s/g, '').toLowerCase().startsWith('data:image')) {
        photoSrc = photoSrc.replace(/\s/g, '');
      }
      data.photoUrl = photoSrc;
    }
  }

  const extendedDetails: Record<string, unknown> = {};

  pages.forEach((page, pageIdx) => {
    const $ = cheerio.load(page.html);

    $('table').each((_i: number, table: Element) => {
      const $table = $(table);
      const rows = $table.find('tr');
      if (rows.length < 2) return;

      let maxCells = 0;
      let headerRowIdx = 0;
      let potentialHeaders: string[] = [];

      rows.slice(0, 3).each((idx: number, row: Element) => {
        const cells = $(row).find('th, td');
        if (cells.length > maxCells) {
          maxCells = cells.length;
          headerRowIdx = idx;
          potentialHeaders = cells
            .map((_: number, el: Element) =>
              $(el)
                .text()
                .trim()
                .replace(/[\r\n]+/g, ' ')
            )
            .get();
        }
      });

      let hasColons = false;
      for (let i = 0; i < potentialHeaders.length; i += 2) {
        if (
          potentialHeaders[i].includes(':') ||
          (i + 1 < potentialHeaders.length &&
            potentialHeaders[i + 1].includes(':'))
        ) {
          hasColons = true;
        }
      }

      let tableName =
        page.name && page.name !== 'Unknown Tab'
          ? page.name
          : `table${pageIdx}_${_i + 1}`;
      const prevHeading = $table
        .prevAll('h1, h2, h3, h4, h5, h6, legend, .panel-heading')
        .first()
        .text()
        .trim();
      const parentHeading = $table
        .parent()
        .prevAll('h1, h2, h3, h4, h5, h6, legend, .panel-heading')
        .first()
        .text()
        .trim();

      let tabLinkName = '';
      const tabPaneId = $table
        .closest('.tab-pane, [id^="tab"], [id^="yt"]')
        .attr('id');
      if (tabPaneId) {
        tabLinkName = $main(`a[href="#${tabPaneId}"]`).text().trim();
      }

      if (tabLinkName) {
        tableName = tabLinkName;
      } else if (
        prevHeading &&
        prevHeading.length > 2 &&
        prevHeading.length < 50
      ) {
        tableName = prevHeading;
      } else if (
        parentHeading &&
        parentHeading.length > 2 &&
        parentHeading.length < 50
      ) {
        tableName = parentHeading;
      } else if (_i > 0 && page.name && page.name !== 'Unknown Tab') {
        tableName = `${page.name} ${_i + 1}`;
      }

      const cleanKey = tableName.replace(/[^a-zA-Z0-9\s]/g, '');
      const finalKey = cleanKey || `section${pageIdx}_${_i + 1}`;

      if (!hasColons) {
        const headers = potentialHeaders;
        if (headers.filter((h: string) => h).length > 0) {
          const tableData: unknown[] = [];
          rows.slice(headerRowIdx + 1).each((_k: number, row: Element) => {
            const cells = $(row)
              .find('td')
              .map((_l: number, el: Element) => {
                const $el = $(el);
                const link = $el.find('a').first();
                if (link.length > 0 && link.attr('href')) {
                  let href = link.attr('href') || '';
                  if (href.startsWith('/'))
                    href = `https://newerp.kluniversity.in${href}`;
                  return {
                    type: 'link',
                    text: $el.text().trim() || 'Link',
                    url: href,
                  };
                }
                return $el.text().trim();
              })
              .get();
            if (cells.length > 0) {
              const rowObj: Record<string, unknown> = {};
              headers.forEach((h: string, idx: number) => {
                if (h) rowObj[h] = cells[idx] || '';
              });
              if (Object.values(rowObj).some((v: unknown) => v !== '')) {
                tableData.push(rowObj);
              }
            }
          });

          if (tableData.length > 0) {
            extendedDetails[finalKey] = tableData;
          }
        }
      } else {
        if (pageIdx === 0) {
          const cells = $table.find('td');
          for (let i = 0; i < cells.length; i += 2) {
            if (i + 1 < cells.length) {
              let label = $(cells[i]).text().trim();
              const value = $(cells[i + 1])
                .text()
                .trim()
                .replace(/^:\s*/, '')
                .trim();
              label = label.replace(/^:\s*/, '').replace(/:$/, '').trim();
              if (label && label.length > 1 && value && value !== ':') {
                if (!extendedDetails[label]) {
                  extendedDetails[label] = value;
                }
                const lKey = label.toLowerCase();
                if (lKey.includes('admission date')) data.admissionDate = value;
                if (lKey.includes('date of birth') || lKey === 'dob')
                  data.dob = value;
                if (lKey.includes('blood group')) data.bloodGroup = value;
                if (lKey.includes('email')) data.email = value;
                if (lKey.includes('height')) data.height = value;
                if (lKey.includes('weight')) data.weight = value;
                if (lKey.includes('regulation')) data.regulation = value;
                if (lKey.includes('program')) data.program = value;
              }
            }
          }
        }
      }
    });
  });

  data.extendedProfile = JSON.stringify(extendedDetails);
  return data;
}
