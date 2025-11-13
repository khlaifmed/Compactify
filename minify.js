const { minify } = require('terser');

const fs = require('fs');
const path = require('path');

async function minifyFile(inputFile, outputFile) {
    // Create output directory if it doesn't exist
    const outputDir = path.dirname(outputFile);
    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, {
            recursive: true
        });
    }

    try {
        const code = fs.readFileSync(inputFile, 'utf8');

        //Use Terser to minify
        const result = await minify(code, {
            compress: {
                passes: 6, // Run compression multiple times for better results
                dead_code: true,
                drop_console: true, // Remove ALL console.* calls
                drop_debugger: true,
                pure_funcs: ['console.log', 'console.info', 'console.debug'],
                unsafe: false,
                unsafe_arrows: false,
                unsafe_comps: false,
                unsafe_math: false,
                unsafe_methods: false,
                unsafe_proto: false,
                unsafe_regexp: false,
                unsafe_undefined: false,
                conditionals: true,
                booleans: true,
                loops: true,
                unused: true,
                hoist_funs: true,
                hoist_props: true,
                hoist_vars: false,
                if_return: true,
                join_vars: true,
                side_effects: true,
                warnings: false,
                global_defs: {
                    DEBUG: false,
                    PRODUCTION: true
                }
            },
            mangle: {
                toplevel: false,
                eval: false,
                keep_classnames: false,
                keep_fnames: false,
                reserved: ['characterId', 'userId', 'action'], //These are specific names for a project it built
                properties: false //keep this false, can break library functions
            },
            format: {
                comments: false,
                ascii_only: false,
                beautify: false,
                braces: false,
                ecma: 2020
            },
            module: true,
            toplevel: false,
            nameCache: null,
            ie8: false,
            safari10: false,
            keep_classnames: false,
            keep_fnames: false
        });

        if (result.error) {
            console.error(`Error minifying ${inputFile}:`, result.error);
            process.exit(1);
        }

        fs.writeFileSync(outputFile, result.code, 'utf8');
        console.log(`✓ Minified: ${inputFile} -> ${outputFile}`);
    } catch (err) {
        console.error(`Error processing ${inputFile}:`, err.message);
        process.exit(1);
    }
}

const inputFile = process.argv[2];
const outputFile = process.argv[3];

if (!inputFile || !outputFile) {
    console.error('Usage: node minify.js <input-file> <output-file>');
    process.exit(1);
}

minifyFile(inputFile, outputFile)
    .then(() => process.exit(0))
    .catch(err => {
        console.error('Fatal error:', err);
        process.exit(1);
    });