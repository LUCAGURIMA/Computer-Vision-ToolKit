"""Architecture Diagram and Summary

This file provides visual and textual summaries of the new modular architecture.
"""

## UML Class Diagram

The system follows a hierarchical OOP structure:

```
┌─────────────────────────────────────────────────────────────────────┐
│                          QMainWindow                                 │
│                        (PyQt5 Base)                                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │inherits
┌──────────────────────────────▼──────────────────────────────────────┐
│                        MainWindow                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ - core: SystemCore                                          │   │
│  │ - capture_mgr: CaptureManagerQt                            │   │
│  │ - inspection_mgr: InspectionManager                        │   │
│  │ - history_mgr: HistoryManager                              │   │
│  │ - pfs_mgr: BaslerProfileManager                            │   │
│  │ - streaming_popup: StreamingPopupWindow                    │   │
│  │ - results_panel: InspectionResultsPanel                    │   │
│  │ + _create_ui()                                             │   │
│  │ + capture_image()                                          │   │
│  │ + perform_inspection()                                     │   │
│  │ + toggle_web_server()                                      │   │
│  │ - _create_capture_tab()                                    │   │
│  │ - _create_inspection_tab()                                 │   │
│  │ - _create_results_tab()                                    │   │
│  │ - _apply_theme()                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘

Composition Relationships:

MainWindow has-a ┌──────────────────────────────────┐
                 │   Threads Module                 │
                 │ ┌────────────────────────────┐   │
                 │ │ CaptureThread (QThread)    │   │
                 │ ├────────────────────────────┤   │
                 │ │ StreamingThread (QThread)  │   │
                 │ ├────────────────────────────┤   │
                 │ │ InspectionThread (QThread) │   │
                 │ └────────────────────────────┘   │
                 └──────────────────────────────────┘

MainWindow has-a ┌──────────────────────────────────┐
                 │   UI Dialogs Module              │
                 │ ┌────────────────────────────┐   │
                 │ │ CropDialog                 │   │
                 │ ├────────────────────────────┤   │
                 │ │ DetectionDialog            │   │
                 │ ├────────────────────────────┤   │
                 │ │ HistoryImageDialog         │   │
                 │ ├────────────────────────────┤   │
                 │ │ CreateProfileDialog        │   │
                 │ ├────────────────────────────┤   │
                 │ │ StreamingPopupWindow       │   │
                 │ └────────────────────────────┘   │
                 └──────────────────────────────────┘

MainWindow has-a ┌──────────────────────────────────┐
                 │   UI Panels Module               │
                 │ ┌────────────────────────────┐   │
                 │ │ InspectionResultsPanel     │   │
                 │ └────────────────────────────┘   │
                 └──────────────────────────────────┘

MainWindow uses  ┌──────────────────────────────────┐
                 │   Utilities                      │
                 │ ┌────────────────────────────┐   │
                 │ │ ImageConverter             │   │
                 │ ├────────────────────────────┤   │
                 │ │ SignalHandlers             │   │
                 │ ├────────────────────────────┤   │
                 │ │ ThemeManager               │   │
                 │ └────────────────────────────┘   │
                 └──────────────────────────────────┘

MainWindow uses  ┌──────────────────────────────────┐
                 │   Managers                       │
                 │ ┌────────────────────────────┐   │
                 │ │ CaptureManagerQt           │   │
                 │ ├────────────────────────────┤   │
                 │ │ InspectionManager          │   │
                 │ ├────────────────────────────┤   │
                 │ │ HistoryManager             │   │
                 │ └────────────────────────────┘   │
                 └──────────────────────────────────┘
```

## Module Dependencies Diagram

```
app.py (MainWindow)
├── imports core/system_core.py
├── imports core/utils/logger.py
├── imports managers/*
├── imports threads/
│   ├── threads/capture_thread.py
│   ├── threads/streaming_thread.py
│   └── threads/inspection_thread.py
├── imports ui/dialogs/
│   ├── ui/dialogs/crop_dialog.py
│   ├── ui/dialogs/detection_dialog.py
│   ├── ui/dialogs/history_image_dialog.py
│   ├── ui/dialogs/create_profile_dialog.py
│   └── ui/dialogs/streaming_popup_window.py
│       └── imports threads/streaming_thread.py
├── imports ui/panels/
│   └── ui/panels/inspection_results_panel.py
└── imports theme/
    └── theme/__init__.py (ThemeManager)
```

## Data Flow Diagram

```
User Interaction
     │
     ▼
   MainWindow
   │   │   │
   │   │   ├─► Managers (capture, inspect, history)
   │   │   │      │
   │   │   │      ▼
   │   │   │   SystemCore (business logic)
   │   │   │
   │   │   └─► Threads (async operations)
   │   │      │
   │   │      ├─► CaptureThread ──────┐
   │   │      ├─► StreamingThread ────┼─► signals
   │   │      └─► InspectionThread ───┤
   │   │
   │   └─► UI Components
   │      │
   │      ├─► Dialogs (crop, detection, profiles)
   │      ├─► Panels (inspection results)
   │      └─► Themes
   │
   └─► Display / Interaction
```

## Class Inheritance Hierarchy

```
QThread
├── CaptureThread
├── StreamingThread
└── InspectionThread

QWidget
├── BaseWidget (abstract base)
└── InspectionResultsPanel (extends QWidget directly)

QDialog
├── CropDialog
├── DetectionDialog
├── HistoryImageDialog
├── CreateProfileDialog
└── StreamingPopupWindow

QObject
├── ImageConverter (utility)
└── SignalHandlers (utility)

QMainWindow
└── MainWindow
```

## Cross-Module Interfaces

```
Dialogs Interface:
- accept() / reject()  ← QDialog standard
- get_*() methods      ← return dialog results

Thread Interface:
- run()                ← QThread implementation
- pyqtSignal emissions ← inter-thread communication
- stop()               ← graceful shutdown

Panel Interface:
- display_results()    ← show new data
- clear_results()      ← reset display
- initialize()         ← setup resources
- cleanup()            ← teardown resources

Utility Interface (static/class methods):
- ImageConverter.numpy_to_qimage()
- ImageConverter.numpy_to_pixmap()
- SignalHandlers.safe_connect()
- ThemeManager.apply_theme()
```

## File Statistics

| Module | Purpose | Lines | Classes |
|--------|---------|-------|---------|
| app.py | Main orchestrator | 1000+ | 1 (MainWindow) |
| capture_thread.py | Image capture | ~45 | 1 |
| streaming_thread.py | Frame streaming | ~65 | 1 |
| inspection_thread.py | ML inference | ~65 | 1 |
| crop_dialog.py | Crop selection | ~130 | 1 |
| detection_dialog.py | Result display | ~200 | 1 |
| history_image_dialog.py | Image viewing | ~45 | 1 |
| create_profile_dialog.py | Profile creation | ~45 | 1 |
| streaming_popup_window.py | Streaming preview | ~140 | 1 |
| inspection_results_panel.py | Results panel | ~250 | 1 |
| image_converter.py | Image utilities | ~60 | 1 |
| signal_handlers.py | Signal utilities | ~40 | 1 |
| theme/__init__.py | Theme management | ~100 | 1 |
| base_widget.py | Widget base | ~45 | 1 |
| **TOTAL** | | ~2400 | 16 |

The refactored code is approximately the same size as the original monolithic
file but is now split across 14 focused modules with clear responsibilities.
