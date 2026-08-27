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
    ],
  },
  externals: {
    react: 'React',
    'react-dom': 'ReactDOM',
    'react-redux': 'ReactRedux',
  },
};
