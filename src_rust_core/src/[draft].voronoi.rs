# file: src_rust_core/src/[draft].voronoi.rs
// filename: rust_core/src/voronoi.rs

use pyo3::prelude::*;
use rusqlite::Connection;
use spade::{DelaunayTriangulation, Point2, Triangulation};
use std::collections::HashMap;

type DT = DelaunayTriangulation<Point2<f64>>;

/// Initializes or resets the territories table in SQLite.
fn setup_territories_table(conn: &Connection) -> PyResult<()> {
    conn.execute("DROP TABLE IF EXISTS territories;", [])
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
    conn.execute(
        "CREATE TABLE territories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            point_id INTEGER NOT NULL,
            r_hop INTEGER NOT NULL,
            polygon_wkt TEXT NOT NULL,
            FOREIGN KEY(point_id) REFERENCES points(id)
        );",
        [],
    ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
    Ok(())
}

/// Retrieves all distinct r_hop ranks in ascending order.
fn fetch_r_hops(conn: &Connection) -> PyResult<Vec<i64>> {
    let mut stmt = conn.prepare("SELECT DISTINCT r_hop FROM points ORDER BY r_hop ASC;")
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
    
    let r_hops = stmt.query_map([], |row| row.get(0))
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?
        .filter_map(Result::ok)
        .collect();
    
    Ok(r_hops)
}

/// Fetches cumulative points up to the target r_hop tier.
fn fetch_cumulative_points(conn: &Connection, target_r: i64) -> PyResult<Vec<(i64, f64, f64)>> {
    let mut stmt = conn.prepare("SELECT id, x, y FROM points WHERE r_hop <= ?1;")
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
    
    let points = stmt.query_map([target_r], |row| {
        Ok((
            row.get::<_, i64>(0)?,
            row.get::<_, f64>(1)?,
            row.get::<_, f64>(2)?,
        ))
    }).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?
      .filter_map(Result::ok)
      .collect();

    Ok(points)
}

#[pyfunction]
pub fn generate_and_store_territories(db_path: &str) -> PyResult<()> {
    let conn = Connection::open(db_path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
    
    setup_territories_table(&conn)?;
    let r_hops = fetch_r_hops(&conn)?;

    for &target_r in &r_hops {
        if target_r == 0 {
            continue;
        }

        let points = fetch_cumulative_points(&conn, target_r)?;
        if points.len() < 3 {
            continue;
        }

        let mut triangulation: DT = DelaunayTriangulation::new();
        let mut id_to_vertex_index = HashMap::new();

        for (id, x, y) in points {
            if let Ok(vertex_handle) = triangulation.insert(Point2::new(x, y)) {
                id_to_vertex_index.insert(vertex_handle.index(), id);
            }
        }

        for vertex in triangulation.vertices() {
            let v_idx = vertex.index();
            if let Some(&point_id) = id_to_vertex_index.get(&v_idx) {
                if let Some(some_edge) = vertex.out_edge() {
                    let first_edge = some_edge;
                    let mut outgoing_edge = first_edge;
                    let mut coords = Vec::new();
                    let mut valid = true;

                    loop {
                        let face = outgoing_edge.face();
                        if let Some(inner_face) = face.as_inner() {
                            let circumcenter = inner_face.circumcenter();
                            coords.push(format!("{} {}", circumcenter.x, circumcenter.y));
                        } else {
                            valid = false;
                            break;
                        }

                        let next_edge = outgoing_edge.next();
                        outgoing_edge = next_edge;
                        if outgoing_edge == first_edge {
                            break;
                        }
                    }

                    if valid && !coords.is_empty() {
                        if coords[0] != *coords.last().unwrap() {
                            coords.push(coords[0].clone());
                        }
                        let wkt = format!("POLYGON(({}))", coords.join(", "));

                        conn.execute(
                            "INSERT INTO territories (point_id, r_hop, polygon_wkt) VALUES (?1, ?2, ?3);",
                            rusqlite::params![point_id, target_r, wkt],
                        ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
                    }
                }
            }
        }
    }

    Ok(())
}