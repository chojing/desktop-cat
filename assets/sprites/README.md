# PNG 스프라이트 규격

`main.py`는 아래 투명 PNG를 자동으로 읽습니다.

| 파일 | 용도 | 권장 프레임 |
|---|---|---|
| `cat_idle.png` | 기본 대기 | 1장 |
| `cat_typing_1.png` | 타이핑 앞발 A | 1장 |
| `cat_typing_2.png` | 타이핑 앞발 B | 1장 |
| `cat_sleep.png` | 수면, 감은 눈 | 1장 |
| `cat_happy.png` | 더블클릭/깨우기 | 1장 |

## 이미지 제작 기준

- PNG, RGBA, 투명 배경
- 권장 원본 크기: `48 x 48` 또는 `64 x 64` 픽셀
- 모든 파일은 같은 캔버스 크기와 같은 고양이 위치를 사용
- 픽셀 아트는 안티앨리어싱 없이 제작
- 투명 여백을 포함해 고양이 발이나 꼬리가 잘리지 않도록 구성
- 앱에서는 각 이미지를 `142 x 142`로 확대하며 보간을 사용하지 않음

파일이 일부 없어도 앱은 기존 코드 기반 픽셀 고양이로 자동 대체됩니다.

## config.yaml 사용법

상태별 파일명은 `config.yaml`에서 변경할 수 있습니다. 배열에 여러 PNG를
넣으면 앱이 약 100ms 간격으로 순서대로 반복 표시합니다.

```yaml
sprites:
  idle:
    - orange_idle_1.png
    - orange_idle_2.png
  typing:
    - orange_typing_1.png
    - orange_typing_2.png
  sleep: orange_sleep.png
  happy:
    - orange_happy_1.png
    - orange_happy_2.png
```

예를 들어 `orange_idle.png` 파일을 이 폴더에 넣고 `idle` 항목을 변경하면
앱을 다시 시작했을 때 해당 이미지가 사용됩니다. 파일명은 PNG만 허용되며,
이 폴더 밖의 파일 경로는 보안상 무시됩니다.
