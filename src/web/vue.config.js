module.exports = {
    runtimeCompiler: true,
    devServer: {
        hot: false,
    },
    configureWebpack: {
        performance: {
            hints: false,
            maxEntrypointSize: 512000,
            maxAssetSize: 512000,
        },
    },
};
