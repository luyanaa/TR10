# Tutorial: How to make Pcell for KLayout by Python API

by jun1okamura 
---
Regardless of the original PDK package from TOKAI RIKA, I would like to remake the PCell script for the KLayout by Python API base step-by-step as a Tutorial and ask the Open-Source Silicon community to provide feedback and/or collaborate to polish it. This is my first deep dive into Klayout Python API and TR-1um technology, so there may be misunderstandings and non-optimized use of the runset command. Please feel free to let me know and guide me to the proper method or command.

I might be one of the first users—and chip designers—in Japan to work with EWS-based EDA software. Back in 1987, I installed the SDA Edge tool on a Sun-3 workstation to design dynamic memory devices. The **SDA Edge** environment included a **SKILL** interpreter, which served as a layout database access language. **SKILL** is a LISP-based language with a C-like coding style and object-oriented extensions for database access. I became deeply familiar with **SKILL** and developed many utility tools to support my design workflow. It proved to be a much more efficient alternative to manual layout operations.

These early experiences greatly shaped my perspective. My current development of KLayout PCells using Python API is based on that background, although it may not fully align with methodologies driven by today’s commercial EDA vendors. 

**IMHO**, the most important principles in PCell development are: Clear documentation and Simple, maintainable code. To support the community, I’ve created a tutorial note (in Japanese) covering Python API and PCell development. If you’re not fluent in Japanese, I recommend using your browser’s auto-translation feature:

**Then, Let's start!**

## [Chapter 1](https://qiita.com/jun1okamura/items/1086d03b144304644779) Layout/Cell Class

## [Chapter 2](https://qiita.com/jun1okamura/items/b1cbc28045b87ddf5d07) Instance Class

## [Chapter 3](https://qiita.com/jun1okamura/items/cc6456bad1edb04c88a2) Cell vs PCell

## [Chapter 4](https://qiita.com/jun1okamura/items/467ded3756383735e902) PCell Library

## [Chapter 5](https://qiita.com/jun1okamura/items/5686f05d771771fc84bd) TR-1um PCell Library

## [Chapter 6](https://qiita.com/jun1okamura/items/354597987cf71365a8ab) PCellDeclarationHelper Class
        