// scripts/preprocess.js

const fs = require('fs/promises');
const path = require('path');

// Configuration for the source repository
const GITHUB_REPO_OWNER = 'Pokerole-Software-Development';
const GITHUB_REPO_NAME = 'Pokerole-Data';
const GITHUB_BRANCH = 'master';
const BASE_PATH = 'Version20';

const GITHUB_TREES_API_URL = `https://api.github.com/repos/${GITHUB_REPO_OWNER}/${GITHUB_REPO_NAME}/git/trees/${GITHUB_BRANCH}?recursive=1`;
const GITHUB_RAW_BASE_URL = `https://raw.githubusercontent.com/${GITHUB_REPO_OWNER}/${GITHUB_REPO_NAME}/${GITHUB_BRANCH}/`;

// The script will place the output files in a new `public/data` directory
const OUTPUT_DIR = path.join(__dirname, '..', 'public', 'data');

/**
 * Fetches a JSON file from a URL.
 * @param {string} url The URL to fetch.
 * @returns {Promise<any>} A promise that resolves to the parsed JSON data.
 */
async function fetchJson(url) {
  try {
    const headers = { 'Accept': 'application/vnd.github.v3+json' };
    // The GITHUB_TOKEN is automatically provided by GitHub Actions
    // and helps prevent API rate limiting.
    if (process.env.GITHUB_TOKEN) {
      headers['Authorization'] = `token ${process.env.GITHUB_TOKEN}`;
    }
    const response = await fetch(url, { headers });
    if (!response.ok) {
      console.warn(`Failed to fetch ${url}, status: ${response.status} ${response.statusText}`);
      return null;
    }
    return await response.json();
  } catch (error) {
    console.error(`Error fetching ${url}:`, error);
    return null;
  }
}

/**
 * Fetches an array of JSON files with limited concurrency for performance.
 * @param {string[]} urls Array of URLs to fetch.
 * @param {number} concurrencyLimit The maximum number of parallel requests.
 * @returns {Promise<any[]>} A promise that resolves to an array of the fetched data.
 */
async function fetchAllJsonsConcurrently(urls, concurrencyLimit = 25) {
    const results = [];
    let currentUrlIndex = 0;

    const worker = async () => {
        while (currentUrlIndex < urls.length) {
            const index = currentUrlIndex++;
            if (index < urls.length) {
                const url = urls[index];
                const data = await fetchJson(url);
                if (data) {
                    results.push(data);
                }
            }
        }
    };
    
    const workerPromises = Array(concurrencyLimit).fill(0).map(worker);
    await Promise.all(workerPromises);
    
    return results;
}

async function main() {
  console.log('Starting data pre-processing...');

  // 1. Fetch the file tree from the source GitHub repository
  console.log('Fetching file tree from GitHub API...');
  const treeData = await fetchJson(GITHUB_TREES_API_URL);
  if (!treeData || !treeData.tree) {
    console.error('Failed to fetch or parse the repository file tree. Aborting.');
    process.exit(1);
  }
  console.log(`Found ${treeData.tree.length} files in the repository tree.`);

  // 2. Filter for the relevant JSON file paths
  const pokemonUrls = [];
  const movesUrls = [];
  const abilitiesUrls = [];

  const pokedexPath = `${BASE_PATH}/Pokedex/`;
  const movesPath = `${BASE_PATH}/Moves/`;
  const abilitiesPath = `${BASE_PATH}/Abilities/`;
  
  for (const item of treeData.tree) {
      if (item.type === 'blob' && item.path.endsWith('.json')) {
          const rawUrl = `${GITHUB_RAW_BASE_URL}${item.path}`;
          if (item.path.startsWith(pokedexPath)) {
              pokemonUrls.push(rawUrl);
          } else if (item.path.startsWith(movesPath)) {
              movesUrls.push(rawUrl);
          } else if (item.path.startsWith(abilitiesPath)) {
              abilitiesUrls.push(rawUrl);
          }
      }
  }

  console.log(`Found ${pokemonUrls.length} Pokémon files to fetch.`);
  console.log(`Found ${movesUrls.length} move files to fetch.`);
  console.log(`Found ${abilitiesUrls.length} ability files to fetch.`);

  // 3. Fetch all the data concurrently
  console.log('Fetching all individual JSON files (this may take a moment)...');
  const [pokemonData, movesData, abilitiesData] = await Promise.all([
    fetchAllJsonsConcurrently(pokemonUrls),
    fetchAllJsonsConcurrently(movesUrls),
    fetchAllJsonsConcurrently(abilitiesUrls),
  ]);

  console.log(`Successfully fetched ${pokemonData.length} Pokémon.`);
  console.log(`Successfully fetched ${movesData.length} moves.`);
  console.log(`Successfully fetched ${abilitiesData.length} abilities.`);

  // 4. Write the combined data to new files
  await fs.mkdir(OUTPUT_DIR, { recursive: true });

  const filesToWrite = [
    { name: 'all_pokemon.json', data: pokemonData },
    { name: 'all_moves.json', data: movesData },
    { name: 'all_abilities.json', data: abilitiesData },
  ];
  
  for (const file of filesToWrite) {
    const filePath = path.join(OUTPUT_DIR, file.name);
    console.log(`Writing ${file.data.length} items to ${filePath}...`);
    await fs.writeFile(filePath, JSON.stringify(file.data, null, 2));
  }

  console.log('✅ Data pre-processing complete!');
}

main().catch(error => {
  console.error('An unexpected error occurred during pre-processing:', error);
  process.exit(1);
});