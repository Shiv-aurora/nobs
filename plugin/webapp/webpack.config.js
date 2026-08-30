const path = require('path');

module.exports = {
  entry: './src/index.tsx',
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'main.js',
    library: 'NoPingPlugin',
    libraryTarget: 'window',
  },
  resolve: {extensions: ['.ts', '.tsx', '.js']},
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        use: {
          loader: 'ts-loader',
          options: {compilerOptions: {noEmit: false}},
        },
        exclude: /node_modules/,
      },
      {test: /\.css$/, use: ['style-loader', 'css-loader']},
      {
        test: /\.(png|jpg|jpeg|gif|webp)$/i,
        type: 'asset/resource',
        generator: {filename: 'assets/[name].[contenthash:8][ext]'},
      },
      {
        test: /\.worklet\.js$/i,
        type: 'asset/resource',
        generator: {filename: 'assets/[name].[contenthash:8][ext]'},
      },
    ],
  },
  externals: {
    react: 'React',
    'react-dom': 'ReactDOM',
    'react-redux': 'ReactRedux',
  },
};
