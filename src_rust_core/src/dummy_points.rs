# file: src_rust_core/src/dummy_points.rs
use gdal::Dataset;
use pyo3::prelude::*;
use rand::Rng;

#[pyclass]
pub struct Sampler {
    cdf: Vec<f64>,
    total_weight: f64,
    width: usize,
    height: usize,
    geotransform: [f64; 6],
}

impl Sampler {
    // --- Strategy 1: True Uniform Area Sampling ---
    fn sample_uniform_strategy(&self, rng: &mut impl Rng) -> (usize, usize) {
        let x_idx = rng.gen_range(0..self.width);
        let y_idx = rng.gen_range(0..self.height);
        (x_idx, y_idx)
    }

    // --- Strategy 2: Population-Weighted Dasymetric Sampling (CDF + Binary Search) ---
    fn sample_dasymetric_strategy(&self, rng: &mut impl Rng) -> (usize, usize) {
        let target: f64 = rng.gen_range(0.0..self.total_weight);
        let idx = match self.cdf.binary_search_by(|v| v.partial_cmp(&target).unwrap()) {
            Ok(i) => i,
            Err(i) => i,
        };
        (idx % self.width, idx / self.width)
    }

    // --- Coordinate Transformation Helper ---
    fn pixel_to_geo(&self, x_idx: usize, y_idx: usize) -> (f64, f64) {
        let lon = self.geotransform[0] + (x_idx as f64 + 0.5) * self.geotransform[1] + (y_idx as f64 + 0.5) * self.geotransform[2];
        let lat = self.geotransform[3] + (x_idx as f64 + 0.5) * self.geotransform[4] + (y_idx as f64 + 0.5) * self.geotransform[5];
        (lon, lat)
    }
}

#[pymethods]
impl Sampler {
    #[new]
    pub fn new(file_path: &str) -> PyResult<Self> {
        let dataset = Dataset::open(file_path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        
        let geotransform = dataset.geo_transform()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

        let band = dataset.rasterband(1)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

        let width = band.x_size();
        let height = band.y_size();
        
        // read_as returns a gdal Buffer<T>; extract the underlying Vec<T> via .data
        let buffer = band.read_as::<f64>(
            (0, 0),
            (width, height),
            (width, height),
            None,
        ).map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

        let raster_data = buffer.data;

        let mut cdf = Vec::with_capacity(raster_data.len());
        let mut cumulative = 0.0;

        for &val in &raster_data {
            let weight = if val.is_nan() || val < 0.0 { 0.0 } else { val };
            cumulative += weight;
            cdf.push(cumulative);
        }

        Ok(Sampler {
            cdf,
            total_weight: cumulative,
            width,
            height,
            geotransform,
        })
    }

    #[pyo3(signature = (num_samples, method = "dasymetric"))]
    pub fn sample_points(&self, num_samples: usize, method: &str) -> PyResult<Vec<(f64, f64)>> {
        let mut rng = rand::thread_rng();
        let mut results = Vec::with_capacity(num_samples);

        for _ in 0..num_samples {
            let (x_idx, y_idx) = match method {
                "uniform" => self.sample_uniform_strategy(&mut rng),
                _ => self.sample_dasymetric_strategy(&mut rng),
            };
            results.push(self.pixel_to_geo(x_idx, y_idx));
        }

        Ok(results)
    }
}

#[pymodule]
fn dummy_points(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Sampler>()?;
    Ok(())
}