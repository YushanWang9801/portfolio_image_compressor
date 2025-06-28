# Portfolio Image Compressor

![Project Status](https://img.shields.io/badge/status-personal%20use%20only-yellow)

## 📌 Introduction

This repository contains a custom image processing pipeline I developed to:
- **Batch compress** portfolio images before Firebase upload
- **Automate resizing** while maintaining visual quality
- **Standardize metadata** for my web portfolio
- **Reduce storage costs** through optimized compression

The tool specifically addresses my workflow of preparing hundreds of high-resolution design/art images for my personal website while balancing quality and performance.

## ⚠️ Important Notice

This repository is **strictly for my personal use** and is not currently structured as a distributable package. 

Key limitations:
- Contains hardcoded Firebase/storage paths specific to my environment
- Requires manual configuration of image processing parameters
- Lacks proper error handling for general use cases
- Assumes specific directory structures on my local machine

## 🔧 Technical Highlights

Current implementation features:
- Custom quality-preserving compression algorithms
- EXIF metadata preservation
- Bulk Firebase Storage upload integration
- Parallel processing capabilities
- Basic progress tracking

## Future Plans

Planned improvements when systematizing:
- [ ] Configurable path mappings
- [ ] Environment variable support
- [ ] Docker containerization
- [ ] Proper CLI interface
- [ ] Comprehensive error handling

## License

While not currently structured for distribution, the code is available under the [MIT License](LICENSE) for reference purposes.

---

*Developed specifically for my Firebase-hosted portfolio - may be generalized in future releases.*