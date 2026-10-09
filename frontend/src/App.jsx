import { useState } from 'react'
import './App.css'

const SIDES = ['front', 'rear', 'left', 'right']
const DAMAGE_SLOTS = [0, 1, 2, 3]
const ZOOM_OPTIONS = [
  { value: 'close', label: 'ใกล้มาก (ครอบคลุม ≈10% ของด้านรถ)' },
  { value: 'medium', label: 'ปานกลาง (≈25%)' },
  { value: 'wide', label: 'ไกล เห็นราวครึ่งด้าน (≈50%)' },
]

const SUPPORTED_CARS = [
  'BMW_X1_2016', 'Ford_Renger_2016', 'Ford_Renger_2019', 'Honda_City_2014',
  'Honda_City_2016', 'Honda_Civic_2013', 'Hyundai_H1_2012', 'Hyundai_H1_2019',
  'Toyota_Fortuner_2011', 'Toyota_Revo_2015', 'Toyota_Vigo_2014',
]

const friendlyError = err =>
  err instanceof TypeError
    ? 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ ตรวจสอบว่า backend กำลังทำงานอยู่'
    : err.message

function groupDamage(points) {
  const groups = {}
  points.forEach(d => {
    const key = `${d.Type}|${d.Severity}`
    if (!groups[key]) groups[key] = { type: d.Type, severity: d.Severity, count: 0 }
    groups[key].count += 1
  })
  return Object.values(groups)
}

function App() {
  // ---- ส่วนระบุรุ่นรถ (เดิม) ----
  const [images, setImages] = useState({})
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [previews, setPreviews] = useState({})

    const handleFileChange = (side, file) => {
    if (previews[side]) URL.revokeObjectURL(previews[side])
      setImages(prev => ({ ...prev, [side]: file }))
      setPreviews(prev => ({ ...prev, [side]: file ? URL.createObjectURL(file) : undefined }))
    }

  const handleSubmit = async () => {
    setError(null)
    for (const side of SIDES) {
      if (!images[side]) {
        setError(`กรุณาอัปโหลดรูปด้าน ${side}`)
        return
      }
    }

    const formData = new FormData()
    SIDES.forEach(side => formData.append(side, images[side]))

    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/identify-car', {
        method: 'POST',
        body: formData,
      })
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail || `Server error: ${response.status}`)
      }
      const data = await response.json()
      setResult(data)
      setCarClass(data.final_class)
    } catch (err) {
      setError(friendlyError(err))
    } finally {
      setLoading(false)
    }
  }

  // ---- ส่วนประเมินความเสียหาย (ใหม่) ----
  const [carClass, setCarClass] = useState('')
  const [damageSlots, setDamageSlots] = useState({})
  const [damageResult, setDamageResult] = useState(null)
  const [damageLoading, setDamageLoading] = useState(false)
  const [damageError, setDamageError] = useState(null)

  const handleDamageFileChange = (slot, file) => {
    setDamageSlots(prev => ({
      ...prev,
      [slot]: { ...prev[slot], file, side: prev[slot]?.side || 'Front', zoom: prev[slot]?.zoom || 'close' },
    }))
  }

  const handleDamageFieldChange = (slot, field, value) => {
    setDamageSlots(prev => ({
      ...prev,
      [slot]: { ...prev[slot], [field]: value },
    }))
  }

  const handleDamageSubmit = async () => {
    setDamageError(null)

    if (!carClass) {
      setDamageError('กรุณาระบุรุ่นรถก่อน (หรือทำขั้นตอนแรกให้เสร็จก่อน)')
      return
    }

    const filledSlots = DAMAGE_SLOTS
      .map(slot => damageSlots[slot])
      .filter(slot => slot && slot.file)

    if (filledSlots.length === 0) {
      setDamageError('กรุณาอัปโหลดรูปความเสียหายอย่างน้อย 1 รูป')
      return
    }

    const formData = new FormData()
    formData.append('car_class', carClass)
    filledSlots.forEach(slot => {
      formData.append('damage_images', slot.file)
      formData.append('zoom_levels', slot.zoom)
      formData.append('sides', slot.side)
    })

    setDamageLoading(true)
    try {
      const response = await fetch('http://localhost:8000/assess-damage', {
        method: 'POST',
        body: formData,
      })
      if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.detail || `Server error: ${response.status}`)
      }
      const data = await response.json()
      setDamageResult(data)
    } catch (err) {
      setDamageError(err.message)
    } finally {
      setDamageLoading(false)
    }
  }

  return (
    <div className="App">
      <header className="hero">
        <h1>Car Damage Assessment</h1>
        <p className="subtitle">EfficientNet + YOLO powered vehicle inspection</p>
      </header>

      <section className="card">
        <h2 className="card-title">Step 1 · Identify Vehicle</h2>
        <details className="supported">
          <summary>รุ่นที่ระบบรองรับ ({SUPPORTED_CARS.length} รุ่น)</summary>
          <p>
            ระบบเลือกคำตอบจากรุ่นเหล่านี้เท่านั้น ถ้าเป็นรถรุ่นอื่นจะถูกทายเป็นรุ่นที่ใกล้เคียงที่สุดในรายการ:{' '}
            {SUPPORTED_CARS.join(', ')}
          </p>
        </details>

        {SIDES.map(side => (
          <div className="field-row" key={side}>
            <label>{side}</label>
            <input
              type="file"
              accept="image/*"
              onChange={e => handleFileChange(side, e.target.files[0])}
            />
          </div>
        ))}

        <button onClick={handleSubmit} disabled={loading}>
          {loading ? 'กำลังวิเคราะห์...' : 'วิเคราะห์รถ'}
        </button>

        {error && <p className="error-text">{error}</p>}

                {result && (
          <div className="result-box">
            <div className="result-main">{result.final_class}</div>
            <div className="result-sub">{result.final_confidence}% confidence</div>
            <div className="result-tags">
              <span className="tag">{result.agreement}</span>
              <span className="tag tag-accent">{result.suggested_base_price.toLocaleString()} บาท</span>
            </div>
            
            {!result.reliable && (
              <div className="warning-box">
                ผลยังไม่แน่นอน: มีน้อยกว่า 3 ใน 4 ด้านที่ทายรุ่นตรงกัน ควรตรวจสอบรุ่นรถอีกครั้ง
              </div>
            )}

            <div className="side-grid">
              {SIDES.map(side => {
                const key = side.charAt(0).toUpperCase() + side.slice(1)
                const r = result.per_side[key]
                return previews[side] && (
                  <div key={side} className="side-card">
                    <img src={previews[side]} alt={side} />
                    <div className="side-caption">
                      <span className="side-name">{key}</span>
                      {r && <span>{r.class} · {r.confidence.toFixed(1)}%</span>}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </section>

      <section className="card">
        <h2 className="card-title">Step 2 · Assess Damage</h2>
        <p className="hint">
          เลือกระดับการซูมให้ตรงกับที่ถ่ายภาพ ระบบใช้ค่านี้ประมาณว่ารอยใหญ่แค่ไหนเมื่อเทียบกับด้านของรถ
        </p>

        <div className="field-row">
          <label>รุ่นรถ</label>
          <input
            type="text"
            value={carClass}
            onChange={e => setCarClass(e.target.value)}
            placeholder="เช่น Honda_Civic_2013"
          />
        </div>

        {DAMAGE_SLOTS.map(slot => (
          <div className="field-row damage-row" key={slot}>
            <input
              type="file"
              accept="image/*"
              onChange={e => handleDamageFileChange(slot, e.target.files[0])}
            />
            <select
              value={damageSlots[slot]?.side || 'Front'}
              onChange={e => handleDamageFieldChange(slot, 'side', e.target.value)}
            >
              {['Front', 'Rear', 'Left', 'Right'].map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <select
              value={damageSlots[slot]?.zoom || 'close'}
              onChange={e => handleDamageFieldChange(slot, 'zoom', e.target.value)}
            >
              {ZOOM_OPTIONS.map(z => (
                <option key={z.value} value={z.value}>{z.label}</option>
              ))}
            </select>
          </div>
        ))}

        <button onClick={handleDamageSubmit} disabled={damageLoading}>
          {damageLoading ? 'กำลังประเมิน...' : 'ประเมินความเสียหาย'}
        </button>

        {damageError && <p className="error-text">{damageError}</p>}

        {damageResult && (
          <div className="result-box">
            <div className="result-main">{damageResult.final_price.toLocaleString()} บาท</div>
            <div className="result-sub">
              ราคากลาง {damageResult.base_price.toLocaleString()} − หัก {damageResult.total_deduction.toLocaleString()} บาท
            </div>
            
            <ul className="damage-list">
              {damageResult.damage_points.map((d, i) => (
                <li key={i}>
                  <span className={`severity-dot ${d.Severity}`} />
                  {d.Side}: {d.Type} ({d.Severity}) — {d.RealPercent}% · conf {d.Confidence}%
                </li>
              ))}
            </ul>

            <div className="image-grid">
              {damageResult.drawn_images.map((img, i) => {
                const points = img.damage_points || []
                const groups = groupDamage(points)
                return (
                  <div key={i} className="image-card">
                    <p>{img.side}</p>
                    <img src={`data:image/jpeg;base64,${img.image_base64}`} alt={img.side} />
                    <div className="damage-summary">
                      {points.length === 0 ? (
                        <span className="summary-none">ไม่พบรอย</span>
                      ) : (
                        <>
                          <span className="summary-total">พบ {points.length} รอย</span>
                          {groups.map(g => (
                            <span key={`${g.type}-${g.severity}`} className="summary-chip">
                              <span className={`severity-dot ${g.severity}`} />
                              {g.type} ({g.severity}) × {g.count}
                            </span>
                          ))}
                        </>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
            <p className="disclaimer">
              ราคานี้เป็นการประเมินเบื้องต้น คำนวณจากจำนวนและระดับของรอย โดยขนาดเทียบกับตัวรถประมาณจากระดับการซูมที่เลือก ไม่ใช่การวัดขนาดจริง
            </p>
          </div>
        )}
      </section>
    </div>
  )
}

export default App